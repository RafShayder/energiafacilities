import psycopg2
import logging
from types import SimpleNamespace
logger=logging.getLogger(__name__)
class BaseRunSP:
    def __init__(self, config: dict):
        self._cfg = SimpleNamespace(**config)
    
    def _connect(self):
        logger.debug("Verificando conectividad a SP PostgreSQL...")
        return psycopg2.connect(
            host=self._cfg.host,
            port=self._cfg.port,
            dbname=self._cfg.database,
            user=self._cfg.user,
            password=self._cfg.password
        )
    #Metodo que corre un sp pasandole como parametro el nombre del sp y
