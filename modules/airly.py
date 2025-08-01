import requests
import json
import os
import logging
from datetime import datetime, timezone

import config
from modules import path_manager
from modules.network_utils import retry

API_URL = "https://airapi.airly.eu/v2/measurements/point"

def get_mock_data():
    """Zwraca dane zastępcze w przypadku błędu."""
    logging.warning("Używam zastępczych danych Airly.")
    return {
        "current": {
            "values": [],
            "indexes": [{"name": "AIRLY_CAQI", "value": 0, "level": "UNKNOWN", "description": "Brak danych"}],
            "standards": []
        }
    }

@retry(exceptions=(requests.exceptions.RequestException,), tries=3, delay=10, backoff=2, logger=logging)
def _fetch_airly_data():
    """Pobiera dane z API Airly z mechanizmem ponawiania prób."""
    if not hasattr(config, 'AIRLY_API_KEY') or not config.AIRLY_API_KEY or config.AIRLY_API_KEY == "TWÓJ_KLUCZ_API_AIRLY":
        logging.error("Brak skonfigurowanego klucza AIRLY_API_KEY w pliku config.py. Pomijam pobieranie danych Airly.")
        return None

    headers = {'apikey': config.AIRLY_API_KEY, 'Accept-Language': 'pl'}
    params = {
        'lat': config.LOCATION_LAT,
        'lng': config.LOCATION_LON
    }
    logging.info(f"Pobieranie danych z API Airly ({API_URL}) dla lokalizacji: lat={config.LOCATION_LAT}, lng={config.LOCATION_LON}")
    response = requests.get(API_URL, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def update_airly_data():
    """
    Pobiera dane o jakości powietrza i pogodzie z API Airly.
    W przypadku błędu, aplikacja będzie korzystać z ostatnich pomyślnie pobranych danych.
    """
    file_path = os.path.join(path_manager.CACHE_DIR, 'airly.json')

    try:
        airly_data = _fetch_airly_data()

        if airly_data:
            # Dodajemy znacznik czasu do zapisywanych danych
            airly_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(airly_data, f, ensure_ascii=False, indent=4)
            logging.info("Pomyślnie zaktualizowano i zapisano dane Airly.")
        else:
            # Jeśli klucz API nie jest skonfigurowany, a plik nie istnieje, stwórz plik z danymi zastępczymi.
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(get_mock_data(), f, ensure_ascii=False, indent=4)

    except requests.exceptions.RequestException as e:
        logging.warning(f"Błąd sieci podczas pobierania danych Airly: {e}. Aplikacja użyje danych z pamięci podręcznej.")
    except Exception as e:
        logging.error(f"Wystąpił nieoczekiwany błąd w module Airly: {e}. Aplikacja użyje danych z pamięci podręcznej.", exc_info=True)
