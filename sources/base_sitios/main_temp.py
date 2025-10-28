
from sources.base_sitios.stractor import extraersftp_energia
from core.utils import setup_logging
from sources.base_sitios.loader import loader_basesitios,loader_bitacora_basesitios
from sources.base_sitios.run_sp import correr_sp_base_sitios

setup_logging("INFO")

#ETL Main

rutaextraida=extraersftp_energia()
loader_basesitios()
loader_bitacora_basesitios()
correr_sp_base_sitios("sftp_base_sitios")
correr_sp_base_sitios("sftp_base_sitios_bitacora")

