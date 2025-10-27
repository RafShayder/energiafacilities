from .help.transform_helpers import ejecutar_transformacion
from core.utils import traerjson,setup_logging,load_config

def load_sftp_web_indra(filepath=None):
    
    config = load_config()
    general_config = config.get("clientes_libres", {})
    mapeo_campos =traerjson(archivo='config/columnas/transformacion.json',valor='clienteslibres')
    
    df = ejecutar_transformacion(general_config, mapeo_campos,save=True )
    return df


setup_logging("INFO")

load_sftp_web_indra()

