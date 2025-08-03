import os
import logging

from modules.config_loader import config

def _find_best_base_dir():
    preferred_dirs = [f'/tmp', '/opt']
    for dir_path in preferred_dirs:
        if os.path.isdir(dir_path) and os.access(dir_path, os.W_OK):
            logging.debug(f"Znaleziono odpowiedni katalog bazowy w RAM: {dir_path}")
            return dir_path

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback_dir = os.path.join(project_root, 'tmp')
    logging.warning(f"Nie znaleziono standardowego katalogu w RAM. Używam lokalnego katalogu awaryjnego: {fallback_dir}")
    return fallback_dir

_BASE_RAM_DIR = _find_best_base_dir()

CACHE_DIR = os.path.join(_BASE_RAM_DIR, config['app']['cache_dir'])

RUNTIME_ASSETS_DIR = os.path.join(CACHE_DIR, 'assets')