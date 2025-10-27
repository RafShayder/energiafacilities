
from core.base_stractor import BaseExtractorSFTP
from core.utils import setup_logging, load_config , generar_archivo_especifico

setup_logging("INFO")

def extraersftp_energia():
    config = load_config()
    sftp_config_connect = config.get("sftp_energia_c", {})
    sftp_config_others =  config.get("sftp_energia", {})
    Extractor = BaseExtractorSFTP(
        config_connect=sftp_config_connect,
        config_paths=sftp_config_others
    )
    Extractor.validar_conexion()
    Extractor.validate() #validar datos del sftp
    archivos=Extractor.listar_archivos()
    archivoextraer=generar_archivo_especifico(lista_archivos=archivos,basearchivo=sftp_config_others['specific_filename'], periodo='202506')
    metastraccion=Extractor.extract(specific_file=archivoextraer)
    return metastraccion

extraersftp_energia()