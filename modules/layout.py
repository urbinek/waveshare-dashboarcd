import logging
import os
import sys
import yaml


LAYOUT_FILE_PATH = 'layout.yaml'

def load_layout():
    """
    Wczytuje i parsuje plik layout.yaml.

    Zwraca:
        dict: Słownik z konfiguracją layoutu, gdzie kluczami są nazwy paneli.
              Zwraca pusty słownik w przypadku błędu.
    """
    if not os.path.exists(LAYOUT_FILE_PATH):
        logging.critical(f"Plik konfiguracyjny layoutu '{LAYOUT_FILE_PATH}' nie został znaleziony.")
        return {}

    logging.info(f"Wczytywanie konfiguracji layoutu z pliku '{LAYOUT_FILE_PATH}'...")
    try:
        with open(LAYOUT_FILE_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logging.info("Konfiguracja layoutu wczytana pomyślnie.")
            return config.get('panels', {})
    except (yaml.YAMLError, IOError) as e:
        logging.critical(f"Błąd podczas wczytywania lub parsowania pliku '{LAYOUT_FILE_PATH}': {e}", exc_info=True)
        return {}
