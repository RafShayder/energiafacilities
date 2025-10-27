
from core.base_stractor import BaseExtractorSFTP
from core.utils import setup_logging, load_config

setup_logging("DEBUG")

def extraersftp_energia():
    config = load_config()
    sftp_config_connect = config.get("sftp_daas_c", {})
    sftp_config_others =  config.get("sftp_base_sitios", {})
    Extractor = BaseExtractorSFTP(
        config_connect=sftp_config_connect,
        config_paths=sftp_config_others
    )
    Extractor.validar_conexion()
    Extractor.validate() #validar datos del sftp
    metastraccion=Extractor.extract()
    return metastraccion

extraersftp_energia() 