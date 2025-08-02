import requests
import json
import os
import logging
from datetime import datetime, timezone, timedelta

import config
from modules import path_manager
from modules.network_utils import retry # Mimo że usuwamy dekorator z jednej funkcji, moduł może być potrzebny gdzie indziej

logger = logging.getLogger(__name__)

# --- Stałe ---
API_BASE_URL = "http://dataservice.accuweather.com"
CURRENT_CONDITIONS_URL = f"{API_BASE_URL}/currentconditions/v1/{config.ACCUWEATHER_LOCATION_KEY}"
DAILY_FORECAST_URL = f"{API_BASE_URL}/forecasts/v1/daily/1day/{config.ACCUWEATHER_LOCATION_KEY}"
LIMIT_FLAG_FILE = os.path.join(path_manager.CACHE_DIR, 'accuweather_limit.flag')

# Usunęliśmy dekorator @retry, aby mieć pełną kontrolę nad obsługą błędów HTTP
def _fetch_accuweather_data(url, params):
    """Pomocnicza funkcja do pobierania danych z API AccuWeather."""
    logger.info(f"Pobieranie danych z API AccuWeather: {url}")
    response = requests.get(url, params=params, timeout=10)
    # Rzuci wyjątkiem (HTTPError) dla odpowiedzi z kodem błędu (4xx lub 5xx)
    response.raise_for_status()
    return response.json()

def update_accuweather_data(verbose_mode=False):
    """Pobiera i zapisuje dane pogodowe z AccuWeather z obsługą limitu zapytań."""
    logger.debug(f"Sprawdzanie pliku flagi limitu: {LIMIT_FLAG_FILE}")
    # 1. Sprawdź, czy flaga limitu istnieje i czy nie minęła godzina
    if os.path.exists(LIMIT_FLAG_FILE):
        logger.debug("Plik flagi limitu istnieje.")
        try:
            with open(LIMIT_FLAG_FILE, 'r') as f:
                last_error_time = datetime.fromisoformat(f.read())
            
            if datetime.now(timezone.utc) - last_error_time < timedelta(hours=1):
                logger.info("Limit zapytań AccuWeather został osiągnięty. Ponowna próba po upływie godziny.")
                return # Zakończ funkcję, nie rób nic więcej
            else:
                logger.info("Minęła godzina od ostatniego błędu limitu. Usuwam flagę i ponawiam próbę.")
                os.remove(LIMIT_FLAG_FILE)
        except (IOError, ValueError) as e:
            logger.warning(f"Nie można odczytać pliku flagi limitu AccuWeather, usuwam go. Błąd: {e}")
            os.remove(LIMIT_FLAG_FILE)
    else:
        logger.debug("Plik flagi limitu nie istnieje.")

    logger.debug(f"ACCUWEATHER_API_KEY: {getattr(config, 'ACCUWEATHER_API_KEY', 'Brak')}")
    logger.debug(f"ACCUWEATHER_LOCATION_KEY: {getattr(config, 'ACCUWEATHER_LOCATION_KEY', 'Brak')}")

    if not all([
        hasattr(config, 'ACCUWEATHER_API_KEY'), config.ACCUWEATHER_API_KEY,
        config.ACCUWEATHER_API_KEY != "TWÓJ_KLUCZ_API_ACCUWEATHER",
        hasattr(config, 'ACCUWEATHER_LOCATION_KEY'), config.ACCUWEATHER_LOCATION_KEY
    ]):
        logger.error("Brak skonfigurowanego klucza API lub klucza lokalizacji AccuWeather.")
        return

    try:
        common_params = {
            "apikey": config.ACCUWEATHER_API_KEY,
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
        # 2. Sprawdzanie kodu błędu 503 (limit przekroczony)
        if e.response.status_code == 503:
            try:
                error_data = e.response.json()
                error_message = error_data.get("Message", "Brak szczegółowej wiadomości od serwera.")
                logger.error(f"Przekroczono limit zapytań AccuWeather. Odpowiedź serwera: \"{error_message}\"")
                # 3. Utwórz plik-flagę z aktualnym czasem
                with open(LIMIT_FLAG_FILE, 'w') as f:
                    f.write(datetime.now(timezone.utc).isoformat())
                logger.info(f"Wstrzymuję zapytania do AccuWeather na 1 godzinę.")
            except json.JSONDecodeError:
                logger.error(f"Przekroczono limit zapytań AccuWeather (odpowiedź serwera nie jest w formacie JSON): {e.response.text}")
        else:
            # Inne błędy HTTP
            logger.warning(f"Wystąpił nieoczekiwany błąd HTTP podczas pobierania danych z AccuWeather: {e}")
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Błąd sieci podczas pobierania danych z AccuWeather: {e}.")
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany, krytyczny błąd w module AccuWeather: {e}", exc_info=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    update_accuweather_data()
