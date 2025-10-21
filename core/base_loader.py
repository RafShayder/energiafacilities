from __future__ import annotations
from tkinter import RAISED
from typing import Any, Dict, Optional
from types import SimpleNamespace
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
logger = logging.getLogger(__name__)

class BaseLoaderPostgres:
    """
    Clase estandar de carga de datos
      - variables: config(parametros de conexión) y configload (parametros de carga)
      - soporta ->  Excel, CSV o DataFrame
      - variable data -> str| df 
      - Inserta por lotes (batch)
      - Permite mapeo opcional de columnas, sino carga toda la data tal cual
    """

    def __init__(self, config: dict, configload: dict):
        if not isinstance(config, dict):
            logger.error("config debe ser un dict con las claves esperadas")
            raise
        if not isinstance(configload, dict):
            logger.error("configload debe ser un dict con los parámetros de carga")
            raise

        self._cfg = SimpleNamespace(**config)
        self._cfgload = SimpleNamespace(**configload)

    # ----------
    #  CONEXIÓN
    # ----------
    def _connect(self):
        logger.info("Se está verificando conectividad a la DB")
        """Crea conexión a PostgreSQL"""

        conexion= psycopg2.connect(
            host=self._cfg.host,
            port=self._cfg.port,
            dbname=self._cfg.database,
            user=self._cfg.user,
            password=self._cfg.password
            )
        return conexion

    # ----------
    #  VALIDAR CONECTIVIDAD
    # ----------
    def validar_conexion(self):
        """Verifica si la conexión al host es exitosa"""
        try:
            self._connect().close()
            retornoinfo= {"status": "success", "code": 200, "etl_msg": f"Conexión exitosa a {self._cfg.host}"}
            logger.info("Se conectó correctamente",extra=retornoinfo)
            return retornoinfo
        except Exception as e:
            retornoinfo={"status": "error", "code": 401, "etl_msg": f"Error de conectividad: {str(e)}"}
            logger.error(f"Error de conectividad: {str(e)}",extra=retornoinfo)
            raise

    # ----------
    #  VERIFICA LAS COLUMNAS DEL JSON
    # ----------
    def verificar_datos(self, data: Any, column_mapping: Optional[Dict[str, str]] = None, sheet_name: str = 0):
        """Verifica columnas entre origen (Excel/CSV/DF) y tabla destino"""
        try:
            # --- Obtener DataFrame origen
            if isinstance(data, pd.DataFrame):
                df = data
                origen = "DataFrame en memoria"
            elif isinstance(data, str) and data.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(data, sheet_name=sheet_name)
                origen = f"Archivo Excel ({data})"
            elif isinstance(data, str) and data.lower().endswith(".csv"):
                df = pd.read_csv(data)
                origen = f"Archivo CSV ({data})"
            else:
                retornoinfo="Formato no soportado (debe ser DataFrame, Excel o CSV)"
                logger.info(retornoinfo)
                raise 
            
            logger.info(f" {origen} leído con {len(df.columns)} columnas.")

            # --- Aplicar mapeo si existe
            if column_mapping:
                df = df.rename(columns=column_mapping)
                logger.info("Mapeo de columnas aplicado -> se estandarizó cabeceras")

            columnas_origen = set(df.columns)

            # --- Obtener columnas de la tabla postgress destino
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_schema =LOWER(%s) AND table_name = LOWER(%s)
                        ORDER BY ordinal_position;
                    """, (self._cfgload.schema, self._cfgload.table))
                    columnas_tabla = {r[0] for r in cur.fetchall()}
            
            # --- comparamos si falta algo (error) o sobra (alerta)  ---        
            sobrantes = columnas_origen - columnas_tabla
            faltantes = columnas_tabla - columnas_origen
       
            if faltantes:
                retornoinfo={
                    "status": "error",
                    "code": 400,
                    "etl_msg": f"Columnas no encontradas en la tabla destino: {', '.join(faltantes)}"
                }
                logger.error("Error de match columnas", extra=retornoinfo)
                raise
            
            logger.info("Verificacion de campos minimos exitoso")
            
            if sobrantes:
                logger.warning(f"la tabla base tiene columnas adicionales que no están en el origen: {', '.join(sobrantes)}")
            
            retornoinfo={"status": "success", "code": 200, "etl_msg": "Columnas verificadas correctamente"}
            logger.info("Columnas verificadas correctamente",extra=retornoinfo)
            
            return retornoinfo
        except Exception as e:
            logger.info(f"Error durante verificación de columnas: {e}")
            raise 

    # ----------
    #  METODO DE CARGA DE DATOS
    # ----------
    def load_data(
        self,
        data: Any,
        sheet_name: str = 0,
        batch_size: Optional[int] = None,
        column_mapping: Optional[Dict[str, str]] = None
    ):
        """Carga datos desde DataFrame, Excel o CSV."""
        try:
            if isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, str) and data.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(data, sheet_name=sheet_name)
            elif isinstance(data, str) and data.lower().endswith(".csv"):
                df = pd.read_csv(data)
            else:
                logger.error("Formato de archivo de entrada no reconocido, (xls,xlsx,csv) <- no encontrado")
                raise 

            if column_mapping:
                df = df.rename(columns=column_mapping)
                columnas_existentes = [c for c in column_mapping.keys() if c in df.columns]
                df = df[columnas_existentes].rename(columns=column_mapping)

            batch = batch_size or getattr(self._cfgload, "chunksize", 10000)
            logger.info(f" Iniciando carga: {len(df)} filas, {len(df.columns)} columnas")
            return self.insert_dataframe(df, batch_size=batch)

        except Exception as e:
            logger.error(f"Error al cargar los datos: {e}")
            raise
        
    # ----------
    #  INSERTAMOS POR LOTES
    # ----------
    def insert_dataframe(self, df: pd.DataFrame, batch_size: int = 10000):
        #se considera 3 politicas('append', 'replace' o 'fail').

        # Validación inicial: DataFrame vacío
        if df.empty:
            retornoinfo={
                "status": "error",
                "code": 204,
                "etl_msg": "DataFrame vacío, no hay datos para insertar"
            }
            logger.error("DataFrame vacío, no hay datos para insertar",extra=retornoinfo)
            raise 
        
        try:
            cols = ', '.join(df.columns)
            full_table = f"{self._cfgload.schema}.{self._cfgload.table}"
            total_rows = len(df)
            modo = getattr(self._cfgload, "if_exists", "replace").lower()

            with self._connect() as conn:
                with conn.cursor() as cur:
                    # Verificar existencia de la tabla destino
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_schema = LOWER(%s)
                            AND table_name = LOWER(%s)
                        );
                    """, (self._cfgload.schema, self._cfgload.table))
                    tabla_existe = cur.fetchone()[0]
                    
                    # Política de inserción: manejo de 'fail', 'replace', 'append'
                    if modo == "fail":
                        if tabla_existe:
                            # FAIL: tabla ya existe → no sobreescribir
                            retornoinfo={
                                "status": "error",
                                "code": 409,
                                "etl_msg": f"La tabla {full_table} ya existe y la política if_exists='fail' impide sobreescribir."
                            }
                            logger.error("Politica de fail no permite crear tabla si ya existe",retornoinfo)
                            raise
                        else:
                            # FAIL: crear automáticamente según el DataFrame
                            columnas_sql = ', '.join([f'"{col}" TEXT' for col in df.columns])
                            create_sql = f'CREATE TABLE {full_table} ({columnas_sql});'
                            cur.execute(create_sql)
                            conn.commit()
                            logger.info(f"Tabla {full_table} creada automáticamente (modo 'fail').")
                            
                    elif modo == "replace":
                        if tabla_existe:
                            cur.execute(f"TRUNCATE TABLE {full_table} RESTART IDENTITY CASCADE;")
                            conn.commit()

                    elif modo == "append":
                        # En modo APPEND, simplemente se agregan filas
                        pass

                    else:
                        retornoinfo={
                            "status": "error",
                            "code": 400,
                            "etl_msg": f"Valor de if_exists no reconocido: '{modo}'. Usa 'append', 'replace' o 'fail'."
                        }
                        logger.error("no se reconoce el tipo de inserción != (append, replace,failt)",retornoinfo)
                        raise

                    # Inserción por lotes
                    insert_sql = f"INSERT INTO {full_table} ({cols}) VALUES %s"

                    for start in range(0, total_rows, batch_size):
                        chunk = df.iloc[start:start + batch_size]
                        values = [tuple(x) for x in chunk.to_numpy()]
                        execute_values(cur, insert_sql, values)
                        conn.commit()
            logger.info(f"{total_rows} filas insertadas correctamente con modo '{modo}'")
            retornoinfo={
                "status": "success",
                "code": 200,
                "etl_msg": f"{total_rows} filas insertadas correctamente con modo '{modo}'"
            }
            return retornoinfo

        # ----------
        #  MANEJO DE ERRORES
        # ----------
        except psycopg2.OperationalError as e:
            # Errores para reintento
            retornoinfo= {
                "status": "error",
                "code": 502,
                "etl_msg": f"Error operativo en PostgreSQL (reintentar): {e}"
            }
            logger.error("Error de postgress operativo, generar reintento",retornoinfo)

        except Exception as e:
            # Errores criticos: formato incorrecto, permisos, etc.
            retornoinfo= {
                "status": "error",
                "code": 500,
                "etl_msg": f"Error durante la inserción: {e}"
            }
            logger.error("Se produjo un error durante la inserción", extra=retornoinfo)
