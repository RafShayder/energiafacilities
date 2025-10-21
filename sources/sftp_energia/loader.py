from core.base_loader import BaseLoaderPostgres
from core import utils
from core.utils import traerjson,setup_logging
setup_logging("INFO")
def extraersftp_energia(filepath=None):
    
    config = utils.load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get("sftp_energia", {})
    Loader = BaseLoaderPostgres(
            config=postgres_config,
            configload=general_config
        )

    Loader.validar_conexion()
    columnas =traerjson(archivo='config/columnas/columns_map.json',valor='tablarecibosenergia')
    Loader.verificar_datos(data=general_config['local_dir'] +'/'+ general_config['specific_filename'] ,column_mapping=columnas)

    if not (filepath):
        filepath=general_config['local_dir'] +'/'+ general_config['specific_filename']
    carga=Loader.load_data(data=filepath, column_mapping=columnas )
    return carga

extraersftp_energia()