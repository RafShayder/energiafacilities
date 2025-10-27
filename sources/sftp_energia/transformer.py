from core.base_exporter import BaseExporterPostgres
from core.utils import load_config,setup_logging

setup_logging("INFO")
def generarlog_sftp():
    config = load_config()
    postgres_config = config.get("postgress", {})
    error_tabla = config.get("sftp_energia",{})
    exporter = BaseExporterPostgres(postgres_config)

    # 1️ Validar conexión
    exporter.validar_conexion()
    # 2️ Extraer tabla
    df = exporter.extract_data(
        error_tabla['errorconfig']
    )

    # 3️ Exportar a Excel
    exporter.export_to_file(df, "tmp/clientes_peru.xlsx")


generarlog_sftp()