from core.base_loader import BaseLoaderPostgres
from core.utils import traerjson,load_config

def load_sftp_energia(filepath=None):
    
    config = load_config()
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

