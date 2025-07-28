import os
import logging

# Import config, aby pobrać bazową nazwę dla naszego katalogu cache
import config

def _find_best_base_dir():
    preferred_dirs = [f'/dev/shm', '/tmp']
    for dir_path in preferred_dirs:
        if os.path.isdir(dir_path) and os.access(dir_path, os.W_OK):
            logging.debug(f"Znaleziono odpowiedni katalog bazowy w RAM: {dir_path}")
            return dir_path

    # Opcja awaryjna, jeśli żaden z powyższych nie jest dostępny.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback_dir = os.path.join(project_root, 'tmp')
    logging.warning(f"Nie znaleziono standardowego katalogu w RAM. Używam lokalnego katalogu awaryjnego: {fallback_dir}")
    return fallback_dir

# Ustal bazowy katalog raz, przy imporcie modułu, aby uniknąć wielokrotnego sprawdzania
_BASE_RAM_DIR = _find_best_base_dir()

# Główna, publiczna ścieżka do katalogu cache'u aplikacji
CACHE_DIR = os.path.join(_BASE_RAM_DIR, config.CACHE_DIR_NAME)
