from core.base_loader import BaseLoaderPostgres
from core.utils import traerjson,setup_logging,load_config

def load_sftp_base_sitos(config_name,jsontablanames,sheetname ,filepath=None): #sftp_base_sitios, tablabasedesitios, Base de Sitios
    
    config = load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get(config_name, {})
    Loader = BaseLoaderPostgres(
            config=postgres_config,
            configload=general_config
        )

    Loader.validar_conexion()
    columnas =traerjson(archivo='config/columnas/columns_map.json',valor=jsontablanames)
    Loader.verificar_datos(data=general_config['local_dir'] +'/'+ general_config['specific_filename'] ,column_mapping=columnas,sheet_name=sheetname)
    
    if not (filepath):
        filepath=general_config['local_dir'] +'/'+ general_config['specific_filename']
    carga=Loader.load_data(data=filepath, column_mapping=columnas,sheet_name=sheetname)
    return carga





setup_logging("INFO")

