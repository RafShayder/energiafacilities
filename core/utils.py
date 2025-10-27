from __future__ import annotations
import logging
from envyaml import EnvYAML
from pathlib import Path
from dotenv import load_dotenv
import os
import io
import shutil
import json
from datetime import date, timedelta
import re
from typing import List, Optional, Any, Dict
from types import SimpleNamespace
import pandas as pd
import paramiko


logger = logging.getLogger(__name__)

 # Funciones globales 
def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True
    )




def load_config(env: str | None = None) -> dict:
    """
    Carga un archivo YAML con soporte automático para variables de entorno .
    Ejemplo de uso en el YAML:
        postgres:
          user: ${POSTGRES_USER}
          password: ${POSTGRES_PASS}

    Si las variables existen en el entorno, se reemplazan automáticamente.

    """
    try:
        # Cargar variables del .env si existe (opcional)

        load_dotenv()
        env = env or os.getenv("ENV_MODE", "dev").lower()
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / f"config_{env}.yaml"
        config_path = f"config/config_{env}.yaml"
        
        if not os.path.exists(config_path):
            logger.error(f"No existe el archivo de configuración: {config_path}")
            raise 
        # Cargar YAML con envyaml (hace el reemplazo automático)
        cfg = EnvYAML(config_path, strict=False)
        return dict(cfg)

    except FileNotFoundError as e:
        logger.error(f"No se encontró el archivo: {e}")
        raise
    except Exception as e:
        logger.error(f"Error al cargar configuración: {e}")
        raise



def asegurar_directorio_sftp(sftp, ruta_completa):

    partes = ruta_completa.strip('/').split('/')
    path_actual = ''
    for parte in partes:
        path_actual += '/' + parte
        try:
            a=sftp.stat(path_actual) 
        except FileNotFoundError:
            logger.info(f"Creando carpeta: {path_actual}")
            sftp.mkdir(path_actual)


def traerjson(archivo='',valor=None):
    
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / archivo

    with open(config_path, 'r',encoding='utf-8') as file:
        datos = json.load(file)
        # Imprimir los datos cargados
        if (valor):
            return datos[valor]
        else:
            return datos



def borrar_ruta(ruta: str):
    """
    Borra el archivo o carpeta indicada.
    Si se pasa la ruta de un archivo, borra ese archivo.
    Si se pasa la ruta de una carpeta, borra la carpeta completa y su contenido.

    Ejemplo:
        borrar_ruta("tmp/sftp_recibps/indra/archivo.xlsx")  # borra solo el archivo
        borrar_ruta("tmp/sftp_recibps/indra")              # borra toda la carpeta 'indra'
    """
    ruta = os.path.abspath(ruta) 

    if not os.path.exists(ruta):
        logger.warning(f"La ruta no existe: {ruta}")
        return

    try:
        if os.path.isfile(ruta):
            os.remove(ruta)
            logger.info(f"Archivo eliminado: {ruta}")

        elif os.path.isdir(ruta):
            shutil.rmtree(ruta)
            logger.info(f"Carpeta eliminada con todo su contenido: {ruta}")
     

        else:
            logger.warning(f"Tipo de ruta desconocido no se eliminó ninguna carpeta temporal: {ruta}")
         

    except Exception as e:
        logger.warning(f"Error al borrar '{ruta}': {e}")
        




 # clase de conexion reutilizable a postgress y retornar la conexion para utiliazrla en otros modulos
class ConexionPostgres:
    def __init__(self, config: dict):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger(__name__)
        

    def conectar(self):
        import psycopg2
        try:
            self.connection = psycopg2.connect(
                host=self.config.get("host"),
                port=self.config.get("port"),
                database=self.config.get("database"),
                user=self.config.get("user"),
                password=self.config.get("password")
            )
            logger.info("Conexión a PostgreSQL establecida correctamente.")
            return self.connection
        except Exception as e:
            logger.error(f"Error al conectar a PostgreSQL ->: {e}")
            raise
    # Cierra la conexión opcional si no se usa with
    def cerrar(self):
        if self.connection:
            self.connection.close()
            logger.debug("Conexión a PostgreSQL cerrada.")
    
    
    # Metodo que recibe una consulta, un sp, o el nombre de una funcion y los parametros si es necesario y lo ejecutay retorna un dataframe
    def ejecutar_consulta(
    self,
    consulta: str,
    parametros: Optional[tuple] = None,
    tipo: str = "query"
    ) -> pd.DataFrame:
        """
        Ejecuta una consulta SQL, una función o un procedimiento almacenado y retorna un DataFrame si hay resultados.
        Parámetros:
            consulta   : str  -> Sentencia SQL o nombre de función/SP.
            parametros : tuple -> Parámetros opcionales.
            tipo       : str  -> 'query', 'func' o 'sp'.

        Retorna:
            pd.DataFrame -> Si hay resultados, los retorna. Si no, retorna un DataFrame vacío.
        """
        try:
            with self.connection.cursor() as cursor:
                tipo = tipo.lower()

                if tipo == "fn":
                    cursor.callproc(consulta, parametros or ())
                elif tipo == "sp":
                    if parametros:
                        placeholders = ", ".join(["%s"] * len(parametros))
                        cursor.execute(f"CALL {consulta}({placeholders});", parametros)
                    else:
                        cursor.execute(f"CALL {consulta}();")
                    self.connection.commit()
                else:  # tipo == "query"
                    cursor.execute(consulta, parametros)
                if cursor.description:
                    filas = cursor.fetchall()
                    if filas:  # Solo crea el DataFrame si hay datos
                        columnas = [desc[0] for desc in cursor.description]
                        df = pd.DataFrame(filas, columns=columnas)
                    else:
                        df = pd.DataFrame()
                else:
                    df = pd.DataFrame()
            self.logger.debug(f"Ejecución de {tipo} '{consulta}' completada correctamente.")
            return df

        except Exception as e:
            self.connection.rollback()  # revertir si hay error
            self.logger.error(f"Error al ejecutar {tipo} '{consulta}': {e}")
            raise
 



 # Funciones especificos de SFTP energia:

def generar_archivo_especifico(
    lista_archivos: List[str],
    basearchivo: Optional[str] = None,
    periodo: Optional[str] = None
) -> Optional[str]:
    """
    Retorna el archivo Excel más reciente según la versión (vX.Y)
    del periodo especificado o, si no se pasa, del mes anterior.

    Ejemplo de nombres esperados:
    RECIBOSENERGIA-202508v5.6.xlsx
    RECIBOSENERGIA-202508v4.9.xlsx
    RECIBOSENERGIA-202508v5.8.xlsx
    """
    if(basearchivo.endswith((".xlsx",".xls",".csv"))):
        return basearchivo
    # -------------------------------
    # Determinar el periodo
    # -------------------------------
    if not periodo:
        hoy = date.today()
        ultimo_dia_mes_anterior = hoy.replace(day=1) - timedelta(days=1)
        periodo = f"{ultimo_dia_mes_anterior.year}{ultimo_dia_mes_anterior.month:02d}"

    # -------------------------------
    # Filtrar por basearchivo y periodo
    # -------------------------------
    archivos_filtrados = [
        f for f in lista_archivos
        if f.endswith(".xlsx")
        and (basearchivo is None or f.startswith(basearchivo))
        and periodo in f
    ]

    logger.info(f"Se encontró los archivos {archivos_filtrados} , se verificará la ultima version")
    if not archivos_filtrados:
        logger.error(f"Archivo no encontrado, verificar si existe el archivo {archivos_filtrados}")
        raise

    # -------------------------------
    # Extraer versión (vX.Y)
    # -------------------------------
    def extraer_version(nombre: str):
        """
        Extrae la versión mayor y menor del nombre de archivo.
        Devuelve una tupla (major, minor) como floats para comparar.
        """
        match = re.search(r"v(\d+)\.(\d+)", nombre)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            return (major, minor)
        else:
            return (0, 0)

    # -------------------------------
    # Obtener el archivo con la mayor versión
    # -------------------------------
    archivo_mas_reciente = max(
        archivos_filtrados,
        key=lambda x: extraer_version(x)
    )

    return archivo_mas_reciente

#Crea carpeta si no existe 
def crearcarpeta(local_dir: str):
    try:
        os.makedirs(local_dir, exist_ok=True)
    except FileExistsError:
        logger.info("La carpeta destino ya existe, no se crea")
        pass
    finally:
        logger.error("No se puede crear la carpeta")
        raise


#Subir a un sftp ("temporal")

class BaseUploaderSFTP:
    """
    Clase estándar para subir archivos o DataFrames al SFTP.
      - Usa config(dict) con parámetros de conexión
      - Permite subir archivos locales (.csv/.xlsx) o directamente un DataFrame
      - Crea directorios remotos si no existen
    """

    def __init__(self, config: dict):
        if not isinstance(config, dict):
            logger.error("config debe ser un dict con las claves esperadas")
            raise ValueError("config debe ser un dict con las claves esperadas")

        self._cfg = SimpleNamespace(**config)

    # ----------
    # VALIDAR CAMPOS NECESARIOS
    # ----------
    def validate(self) -> Dict[str, Any]:
        required = ["host", "port", "username", "remote_dir"]
        missing = [k for k in required if not getattr(self._cfg, k, None)]
        if missing:
            retornoinfo = {
                "status": "error",
                "code": 400,
                "etl_msg": f"Faltan campos en config: {missing}"
            }
            logger.error("Faltan campos de conexión", extra=retornoinfo)
            raise ValueError(f"Faltan campos requeridos: {missing}")

        retornoinfo = {"status": "success", "code": 200, "etl_msg": "Campos mínimos validados"}
        logger.info("Campos mínimos de conexión verificados", extra=retornoinfo)
        return retornoinfo

    # ----------
    # VALIDAR CONEXIÓN
    # ----------
    def validar_conexion(self):
        try:
            transport = paramiko.Transport((self._cfg.host, self._cfg.port))
            transport.connect(username=self._cfg.username, password=self._cfg.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.close()
            transport.close()
            retornoinfo = {"status": "success", "code": 200, "etl_msg": "Conexión SFTP exitosa"}
            logger.info("Conexión SFTP validada correctamente", extra=retornoinfo)
            return retornoinfo
        except Exception as e:
            retornoinfo = {"status": "error", "code": 401, "etl_msg": f"Error de conectividad: {e}"}
            logger.error("Error de conexión SFTP", extra=retornoinfo)
            raise

    # ----------
    # ASEGURAR DIRECTORIO REMOTO
    # ----------
    def _asegurar_directorio_sftp(self, sftp, remote_path: str):
        """Crea directorios remotos si no existen"""
        dirs = remote_path.strip("/").split("/")
        current = ""
        for d in dirs:
            current += "/" + d
            try:
                sftp.stat(current)
            except IOError:
                sftp.mkdir(current)
                logger.info(f"Directorio remoto creado: {current}")

    # ----------
    # SUBIR ARCHIVO O DATAFRAME
    # ----------
    def upload(
        self,
        data: Any,
        remote_filename: str,
        file_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sube un DataFrame o un archivo local (.csv/.xlsx) al SFTP remoto.

        Parámetros:
        - data: pd.DataFrame | str (ruta local del archivo)
        - remote_filename: nombre final en el servidor SFTP (ejemplo: 'reportes/reporte.xlsx')
        - file_format: opcional ('csv' o 'xlsx') si se pasa un DataFrame
        """
        self.validate()

        try:
            # Crear conexión
            transport = paramiko.Transport((self._cfg.host, self._cfg.port))
            transport.connect(username=self._cfg.username, password=self._cfg.password)
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Crear directorio remoto si no existe
            remote_dir = self._cfg.remote_dir.rstrip("/")
            self._asegurar_directorio_sftp(sftp, remote_dir)

            # Ruta completa en el SFTP
            remote_path = f"{remote_dir}/{remote_filename}"

            # Caso 1: si es DataFrame, exportarlo temporalmente en memoria
            if isinstance(data, pd.DataFrame):
                file_format = (file_format or "csv").lower()

                if file_format == "csv":
                    with io.BytesIO() as buffer:
                        data.to_csv(buffer, index=False, encoding="utf-8-sig")
                        buffer.seek(0)
                        sftp.putfo(buffer, remote_path)
                elif file_format in ("xlsx", "xls"):
                    with io.BytesIO() as buffer:
                        data.to_excel(buffer, index=False, engine="openpyxl")
                        buffer.seek(0)
                        sftp.putfo(buffer, remote_path)
                else:
                    raise ValueError("Formato no soportado. Usa 'csv' o 'xlsx'.")

            # Caso 2: si es ruta de archivo existente
            elif isinstance(data, str) and os.path.exists(data):
                sftp.put(data, remote_path)

            else:
                raise ValueError("El parámetro 'data' debe ser un DataFrame o una ruta de archivo válida")

            sftp.close()
            transport.close()

            retornoinfo = {
                "status": "success",
                "code": 200,
                "etl_msg": f"Archivo subido correctamente a {remote_path}",
                "remote_path": remote_path
            }
            logger.info("Archivo subido exitosamente", extra=retornoinfo)
            return retornoinfo

        except Exception as e:
            retornoinfo = {
                "status": "error",
                "code": 500,
                "etl_msg": f"Error durante la subida al SFTP: {e}"
            }
            logger.error("Error durante la subida al SFTP", extra=retornoinfo)
            raise
