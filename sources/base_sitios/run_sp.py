import logging

from core.base_postgress import PostgresConnector
from core.utils import load_config

logger = logging.getLogger(__name__)

def correr_sp_base_sitios(sftp_config_name): #sftp_base_sitios
    config = load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get(sftp_config_name, {})
   
    # Crear instancia de conexión
    postgress = PostgresConnector(postgres_config)
    
    sp_ejecutar=general_config['sp_transformacion_tabla']
    postgress.ejecutar(sp_ejecutar, tipo='sp')
    data=postgress.ejecutar("public.log_sp_ultimo_fn",parametros=(f'{sp_ejecutar}()',),tipo='fn')
    logger.info(f"Estado SP: {data['estado'].values}, Detalle: {data['msj_error'].values}")
    data.to_excel("log_sp_ultimo_fn.xlsx")

   