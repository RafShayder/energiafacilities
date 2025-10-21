
from core.base_stractor import BaseExtractorSFTP
from core import utils
utils.setup_logging("INFO")

def extraersftp_energia():
    config = utils.load_config()
    sftp_config = config.get("sftp_energia", {})
    Extractor = BaseExtractorSFTP(
        config=sftp_config
    )
    Extractor.validar_conexion()
    Extractor.validate() #validar datos
    metastraccion=Extractor.extract()
    return metastraccion

extraersftp_energia()