from __future__ import annotations
from typing import Any, Dict
import os
import paramiko
from types import SimpleNamespace
from core.utils import asegurar_directorio_sftp
import logging

logger=logging.getLogger(__name__)
class BaseExtractorSFTP():
    """
      Clase estandar de extracción de datos
      - variables: config(parametros de conexión al sftp) 
      - soporta ->  extrae todo tipo de archivo
      - permite verificar conectividad y parametros necesarios para conexion
    """
    
    def __init__(self, config: dict):
        
        super().__init__()
        if not isinstance(config, dict):
            logger.error("config debe ser un dict con las claves esperadas")
            raise 
        
        self._cfg: Dict[str, Any] = config
        self._cfg_obj = SimpleNamespace(**config)
    # ----------
    #  VALIDA CAMPOS OBLIGATORIOS
    # ----------   
    def validate(self) -> None:
        c = self._cfg
        required = ["host", "port", "username", "remote_dir", "specific_filename", "local_dir"]
        missing = [k for k in required if k not in c or c[k] in (None, "")]
        if missing:
            retornoinfo={
                "status": "error",
                "code": 500,
                "etl_msg": f"Flata campos {missing}"
                }
            logger.error("falta campos de conectividad y extraccion al sftp",extra=retornoinfo)
            raise
        
        retornoinfo={
                "status": "success",
                "code": 200,
                "etl_msg": f"Todo correcto"
            }
        logger.info("campos minimos necesarios comprobado")
        return retornoinfo
       
    @property
    def config(self) -> SimpleNamespace:
        "Acceso por atributos: e.g. self.config.host"
        return self._cfg_obj
    
    # ----------
    #  VALIDAR CONEXION
    # ----------
    def validar_conexion(self):
        try:
            transport = paramiko.Transport((self.config.host, self.config.port))
            usuario = self.config.username
            password = self.config.password
            transport.connect(username=usuario, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.close()
            transport.close()
            logger.info(f"Conexión exitosa al sftp {self.config.host}")

            retornoinfo= {
            "status": "success",
            "code": 200,
            "etl_msg": "Conexión exitosa"
            }
            return retornoinfo
        except Exception as e:
            retornoinfo={
                "status": "error",
                "code": 401,
                "etl_msg": f"Error de conectividad, :  {str(e)}"
            }
            logger.error(f"Error de conectividad {e}",extra=retornoinfo)
  
        
       
    # ----------
    #  EXTRAE DATOS
    # ----------
    def extract(self,remotetransfere=False) -> str:
        """
            Tiene dos formas
            1: remotetransfere: Falso, descarga la data en el ruta lacal que se pasa
            2: remotetransfere: True, transfiere la data a la ruta en el host, tomando como ruta local_dir
        """
        try:
            
            transport = paramiko.Transport((self.config.host, self.config.port))
            usuario=self.config.username
            password=self.config.password
            rutasftp=self.config.remote_dir
            archivo=self.config.specific_filename
            ruta_local=self.config.local_dir
            transport.connect(username=usuario, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
        
            if(remotetransfere):

                asegurar_directorio_sftp(sftp, ruta_local)
                sftp.rename(rutasftp + '/' + archivo, ruta_local + '/' + archivo)
            
                logger.info(f"Archivo movido con éxito de {rutasftp+'/'+archivo} a {ruta_local}")

            else:    
                try:
                    os.makedirs(ruta_local, exist_ok=True)
                    logger.info(f"Se creó la ruta para mover : {ruta_local}")

                except:
                    logger.info("la carpeta ya existe, no se crea carpeta para mover")
                    
                sftp.get(rutasftp+'/'+archivo, ruta_local+'/'+archivo)
            
            sftp.close()    
            transport.close()
            logger.info(f"se extrajo correctamente el archivo ruta: {ruta_local+'/'+archivo }")
            retornoinfo= {
            "status": "success",
            "code": 200,
            "etl_msg": "se extrajo correctamente en "+ ruta_local+'/'+archivo ,
            "ruta": ruta_local+'/'+archivo
            }
            return retornoinfo
        
        except Exception as e:
            retornoinfo= {
            "status": "error",
            "code": 500,
            "etl_msg": f"Error de estracción, error->: {e}"
            }
            logger.error(f"Error de extracción {e}" , extra=retornoinfo)


