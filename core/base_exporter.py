from __future__ import annotations
from typing import Optional, Dict, Any
from types import SimpleNamespace
import pandas as pd
from sqlalchemy import create_engine, text
import logging
import warnings

# Silencia advertencias de compatibilidad pandas/SQLAlchemy
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)

class BaseExporterPostgres:
    """
    Clase estándar de extracción de datos desde PostgreSQL.
    
    - Usa SQLAlchemy para conexión (recomendado por pandas)
    - Recibe un único diccionario 'configextractdata' con los parámetros de extracción
    - Retorna un DataFrame o permite exportar a CSV/Excel
    - Compatible con Airflow u orquestadores ETL
    """

    def __init__(self, config: dict):
        if not isinstance(config, dict):
            logger.error("config debe ser un dict con las claves esperadas (host, port, database, user, password)")
            raise ValueError("config debe ser un dict con las claves esperadas")

        self._cfg = SimpleNamespace(**config)

    # -------------------------
    # CONEXIÓN (SQLAlchemy)
    # -------------------------
    def _connect(self):
        """Crea un engine SQLAlchemy para PostgreSQL"""
        try:
            engine_str = (
                f"postgresql+psycopg2://{self._cfg.user}:{self._cfg.password}"
                f"@{self._cfg.host}:{self._cfg.port}/{self._cfg.database}"
            )
            engine = create_engine(engine_str)
            logger.info(f"Conexión SQLAlchemy establecida con {self._cfg.host}")
            return engine
        except Exception as e:
            logger.error(f"Error creando engine SQLAlchemy: {e}")
            raise

    # -------------------------
    # VALIDAR CONEXIÓN
    # -------------------------
    def validar_conexion(self):
        """Verifica la conexión al motor PostgreSQL"""
        try:
            engine = self._connect()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            retornoinfo = {
                "status": "success",
                "code": 200,
                "etl_msg": f"Conexión exitosa a {self._cfg.host}"
            }
            logger.info("Conexión validada exitosamente", extra=retornoinfo)
            return retornoinfo
        except Exception as e:
            retornoinfo = {
                "status": "error",
                "code": 401,
                "etl_msg": f"Error de conectividad: {str(e)}"
            }
            logger.error("Error de conectividad", extra=retornoinfo)
            raise

    # -------------------------
    # EXTRACCIÓN DE DATOS
    # -------------------------
    def extract_data(self, configextractdata: dict) -> pd.DataFrame:
        """
        Extrae datos de una tabla PostgreSQL según los parámetros definidos en configextractdata.

        Ejemplo de configextractdata:
        {
            "schema": "public",
            "table": "clientes",
            "columns": ["id", "nombre", "pais"],
            "where": "pais = 'PERU'",
            "limit": 100,
            "batch_size": 5000
        }
        """
        if not isinstance(configextractdata, dict):
            logger.error("configextractdata debe ser un dict con parámetros de extracción")
            raise ValueError("configextractdata debe ser un dict")

        cfgext = SimpleNamespace(**configextractdata)

        try:
            # Armar SQL dinámico
            cols = ", ".join(cfgext.columns) if getattr(cfgext, "columns", None) else "*"
            sql = f"SELECT {cols} FROM {cfgext.schema}.{cfgext.table}"

            if getattr(cfgext, "where", None):
                sql += f" WHERE {cfgext.where}"
            if getattr(cfgext, "limit", None):
                sql += f" LIMIT {cfgext.limit}"

            logger.info(f"Ejecutando consulta SQL: {sql}")

            # Ejecutar y devolver DataFrame
            engine = self._connect()
            df = pd.read_sql_query(text(sql), engine, chunksize=getattr(cfgext, "batch_size", None))

            if isinstance(df, pd.io.parsers.TextFileReader):  # Si se usa paginación
                df = pd.concat(df, ignore_index=True)

            retornoinfo = {
                "status": "success",
                "code": 200,
                "etl_msg": f"Extracción completada ({len(df)} filas)"
            }
            logger.info("Extracción completada correctamente", extra=retornoinfo)
            return df

        except Exception as e:
            retornoinfo = {
                "status": "error",
                "code": 500,
                "etl_msg": f"Error durante la extracción: {e}"
            }
            logger.error("Error durante la extracción", extra=retornoinfo)
            raise

    # -------------------------
    # EXPORTACIÓN A ARCHIVO
    # -------------------------
    def export_to_file(
        self,
        df: pd.DataFrame,
        output_path: str,
        index: bool = False
    ) -> Dict[str, Any]:
        """Exporta un DataFrame a CSV o Excel"""
        try:
            if output_path.lower().endswith(".csv"):
                df.to_csv(output_path, index=index, encoding="utf-8-sig")
            elif output_path.lower().endswith(("xlsx","xls")):
                df.to_excel(output_path, index=index, engine="openpyxl")
            else:
                logger.error("Formato no soportado. Usa 'csv' o 'xlsx'.")
                raise 

            retornoinfo = {
                "status": "success",
                "code": 200,
                "etl_msg": f"Archivo exportado correctamente a {output_path}"
            }
            logger.info("Exportación completada correctamente", extra=retornoinfo)
            return retornoinfo
        except Exception as e:
            retornoinfo = {
                "status": "error",
                "code": 500,
                "etl_msg": f"Error al exportar archivo: {e}"
            }
            logger.error("Error durante exportación", extra=retornoinfo)
            raise
