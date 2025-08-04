import requests
import json
import os
import logging
from datetime import datetime, timezone, timedelta

from modules.config_loader import config
from modules import path_manager

logger = logging.getLogger(__name__)

# --- Stałe ---
API_BASE_URL = "http://dataservice.accuweather.com"
ACCUWEATHER_CONFIG = config['api_keys']
CURRENT_CONDITIONS_URL = f"{API_BASE_URL}/currentconditions/v1/{ACCUWEATHER_CONFIG['accuweather_location_key']}"
DAILY_FORECAST_URL = f"{API_BASE_URL}/forecasts/v1/daily/1day/{ACCUWEATHER_CONFIG['accuweather_location_key']}"
def _fetch_accuweather_data(url, params):
    """Pomocnicza funkcja do pobierania danych z API AccuWeather."""
    logger.info(f"Pobieranie danych z API AccuWeather: {url}")
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def update_accuweather_data(verbose_mode=False):
    """Pobiera i zapisuje dane pogodowe z AccuWeather."""
    api_key = ACCUWEATHER_CONFIG.get('accuweather')
    location_key = ACCUWEATHER_CONFIG.get('accuweather_location_key')

    logger.debug(f"ACCUWEATHER_API_KEY: {api_key or 'Brak'}")
    logger.debug(f"ACCUWEATHER_LOCATION_KEY: {location_key or 'Brak'}")

    if not all([
        api_key,
        location_key
    ]):
        logger.error("Brak skonfigurowanego klucza API lub klucza lokalizacji AccuWeather.")
        return

    try:
        common_params = {
            "apikey": api_key,
            "language": "pl-pl",
            "details": "true",
            "metric": "true"
        }

        current_conditions = _fetch_accuweather_data(CURRENT_CONDITIONS_URL, common_params)
        daily_forecast = _fetch_accuweather_data(DAILY_FORECAST_URL, common_params)

        logger.debug(f"Pobrane bieżące warunki: {current_conditions}")
        logger.debug(f"Pobrana prognoza dzienna: {daily_forecast}")

        if current_conditions and daily_forecast:
            data_to_save = {
                "current": current_conditions[0],
                "forecast": daily_forecast['DailyForecasts'][0],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            file_path = os.path.join(path_manager.CACHE_DIR, 'accuweather.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            logger.info("Pomyślnie zaktualizowano i zapisano dane AccuWeather.")
        else:
            logger.warning("Pobrane dane AccuWeather są puste lub niekompletne. Nie zapisano pliku accuweather.json.")

    except requests.exceptions.HTTPError as e:
        logger.error(f"Błąd HTTP podczas pobierania danych z AccuWeather: Status {e.response.status_code}, Odpowiedź: {e.response.text}")
        logger.warning(f"Wystąpił nieoczekiwany błąd HTTP podczas pobierania danych z AccuWeather: {e}")

    except requests.exceptions.RequestException as e:
        logger.warning(f"Błąd sieci podczas pobierania danych z AccuWeather: {e}.")
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany, krytyczny błąd w module AccuWeather: {e}", exc_info=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    update_accuweather_data()
