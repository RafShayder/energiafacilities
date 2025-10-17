from core.base_loader import BaseLoaderPostgres
from core import utils
from core.utils import traerjson

def extraersftp_energia():
    config = utils.load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get("sftp_energia", {})
    Loader = BaseLoaderPostgres(
            config=postgres_config,
            configload=general_config
        )

    conectividad=Loader.validar_conexion()
    if not (conectividad['status']=="success"):
        return conectividad
    
    columnas =traerjson(archivo='config/columnas/columns_map.json',valor='tablarecibosenergia')
    camposvalidos=Loader.verificar_datos(data=general_config['local_dir'] +'/'+ general_config['specific_filename'] ,column_mapping=columnas)
    
    if not (camposvalidos['status']=="success"):
        return camposvalidos
    carga=Loader.load_data(data=general_config['local_dir'] +'/'+ general_config['specific_filename'], column_mapping=columnas )
    return carga

estadocarga=extraersftp_energia()

print(estadocarga)
