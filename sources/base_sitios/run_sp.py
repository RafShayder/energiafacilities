import logging

from core.utils import ConexionPostgres
from core.utils import load_config,setup_logging

logger = logging.getLogger(__name__)

def correr_sp_base_sitios(sftp_config_name): #sftp_base_sitios
    config = load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get(sftp_config_name, {})
   
    # Crear instancia de conexión
    conexion = ConexionPostgres(postgres_config)

    # Validar usamos conexion i usamos con with conectar
    with conexion.conectar() as conn:

            with conn.cursor() as cursor:
                
                sp_ejecutar=general_config['sp_transformacion_tabla']
                try:
                    # Llamar al SP para transfeir datos
                    conexion.ejecutar_consulta(sp_ejecutar,tipo='sp')         
                    # Llamar a la func para traer la tabla de log
                    data=conexion.ejecutar_consulta("public.log_sp_ultimo_fn",parametros=(f'{sp_ejecutar}()',),tipo='fn')
                    logger.info(f"Estado SP: {data['estado']}, Detalle: {data['msj_error']}")
                except Exception as e:
                    logger.error(f"Error al ejecutar el procedimiento almacenado: {e}")
                    raise


   
setup_logging("INFO")        
correr_sp_base_sitios("sftp_base_sitios")