from __future__ import annotations
import logging
import os
import yaml
from core.exceptions import ConfigError #agregar las excepciones

def osraiz() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )


def load_config(pathrelative: str) -> dict:
    try:
        with open(pathrelative, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"No existe el archivo de configuración: {pathrelative}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"Error al parsear YAML: {e}") from e


