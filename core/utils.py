from __future__ import annotations
import logging
from envyaml import EnvYAML
from pathlib import Path
from dotenv import load_dotenv
import os
import shutil
import json


logger = logging.getLogger(__name__)

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
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

    with open(config_path, 'r') as file:
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
        
