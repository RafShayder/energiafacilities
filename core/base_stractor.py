from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict
import os
import paramiko
from types import SimpleNamespace
from core.exceptions import RetryableExtractError, NonRetryableExtractError



class BaseExtractorSFTP():
    def __init__(self, config: dict):
        
        super().__init__()
        if not isinstance(config, dict):
            raise TypeError("config debe ser un dict con las claves esperadas")
        
        self._cfg: Dict[str, Any] = config
        self._cfg_obj = SimpleNamespace(**config)
        
    def validate(self) -> None:
        c = self._cfg
        required = ["host", "port", "username", "remote_dir", "specific_filename", "local_dir"]
        missing = [k for k in required if k not in c or c[k] in (None, "")]
        print("validó campos de forma exitosa")
        if missing:
            raise NonRetryableExtractError(f"Config SFTP faltante: {missing}")
         
    @property
    def config(self) -> SimpleNamespace:
        "Acceso por atributos: e.g. self.config.host"
        return self._cfg_obj
    
    def validar_conexion(self):
        try:
            transport = paramiko.Transport((self.config.host, self.config.port))
            usuario = self.config.username
            password = self.config.password
            transport.connect(username=usuario, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.close()
            transport.close()
            print('conexion exitosa')
            return "conexion exitosa"
        except Exception as e:
            print('error de conexion', e)
            return str(e)
 
    def extract(self) -> str:
        try:
            
            transport = paramiko.Transport((self.config.host, self.config.port))
            usuario=self.config.username
            password=self.config.password
            rutasftp=self.config.remote_dir
            archivo=self.config.specific_filename
            ruta_local=self.config.local_dir
            transport.connect(username=usuario, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
           
            
            try:

                os.makedirs(ruta_local, exist_ok=True)
  
                print("se creó : ",ruta_local)
            except:
                print('la carpeta ya existe')
            
            sftp.get(rutasftp+'/'+archivo, ruta_local+'/'+archivo)
            sftp.close()    
            transport.close()
            print("se extrajo correctamente")
            return ruta_local+'/'+archivo
        except Exception as e:
            print('error de extracción', e)
            return str(e)


