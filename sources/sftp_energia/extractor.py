import os
from numpy import extract
import paramiko
#importamos el base extractor
from core.base_stractor import BaseExtractorSFTP
#importamos el utils para leer la configuracion
from core import utils


config = utils.load_config("config/config_dev.yaml")

sftp_config = config.get("sftp_energia", {})


  
Extractor = BaseExtractorSFTP(
    config=sftp_config
)

Extractor.validar_conexion()
Extractor.validate()

Extractor.extract()
