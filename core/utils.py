from __future__ import annotations
import logging
from envyaml import EnvYAML
from dotenv import load_dotenv
import os
from core.exceptions import ConfigError #agregar las excepciones
import json
def osraiz() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )


class ConfigError(Exception):
    """Excepción personalizada para errores de configuración."""
    pass

def load_config(env: str | None = None) -> dict:
    """
    Carga un archivo YAML con soporte automático para variables de entorno .
    Ejemplo de uso en el YAML:
        postgres:
          user: ${POSTGRES_USER}
          password: ${POSTGRES_PASS}

    Si las variables existen en el entorno, se reemplazan automáticamente.

    """
    try:
        # Cargar variables del .env si existe (opcional)

        load_dotenv()
        env = env or os.getenv("ENV_MODE", "dev").lower()
        config_path = f"config/config_{env}.yaml"
        
        if not os.path.exists(config_path):
            raise ConfigError(f"No existe el archivo de configuración: {config_path}")
        # Cargar YAML con envyaml (hace el reemplazo automático)
        cfg = EnvYAML(config_path, strict=False)
        return dict(cfg)

    except FileNotFoundError as e:
        raise ConfigError(f"No se encontró el archivo: {e}") from e
    except Exception as e:
        raise ConfigError(f"Error al cargar configuración: {e}") from e



def asegurar_directorio_sftp(sftp, ruta_completa):

    partes = ruta_completa.strip('/').split('/')
    path_actual = ''
    for parte in partes:
        path_actual += '/' + parte
        try:
            a=sftp.stat(path_actual) 
        except FileNotFoundError:
            print(f"Creando carpeta: {path_actual}")
            sftp.mkdir(path_actual)


def traerjson(archivo='config/columns_map.json',valor=None):

    with open(archivo, 'r') as file:
        datos = json.load(file)
        # Imprimir los datos cargados
        if (valor):
            return datos[valor]
        else:
            return datos

def cofiguracion_standar():
    # modo dev modo prod 
    return 