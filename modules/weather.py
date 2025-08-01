import requests
import json
import os
import logging
from datetime import date, datetime, timezone
from dateutil import tz
# Astral to biblioteka do obliczeń astronomicznych, w tym wschodów/zachodów słońca
try:
    from astral.sun import sun
    from astral import LocationInfo
    ASTRAL_AVAILABLE = True
except ImportError:
    ASTRAL_AVAILABLE = False
    logging.warning("Biblioteka 'astral' nie jest zainstalowana (`pip install astral`). Dane o wschodzie/zachodzie słońca nie będą dostępne.")

import config
from modules import path_manager
from modules.network_utils import retry

def get_mock_data():
    """Zwraca dane zastępcze w przypadku błędu."""
    logging.warning("Używam zastępczych danych pogodowych.")
    return {
        "icon": config.ICON_SYNC_PROBLEM_PATH,
        "temp_real": "--",
        "sunrise": "--:--",
        "sunset": "--:--",
        "humidity": "--",
        "pressure": "--",
    }

def _get_sunrise_sunset():
    """Oblicza czas wschodu i zachodu słońca dla lokalizacji z konfiguracji."""
    if not ASTRAL_AVAILABLE:
        return "--:--", "--:--"
    try:
        # Zdefiniuj lokalizację z poprawną strefą czasową, aby uzyskać dokładne wyniki
        loc = LocationInfo("Katowice", "Poland", "Europe/Warsaw", config.LOCATION_LAT, config.LOCATION_LON)
        s = sun(loc.observer, date=date.today())

        # API zwraca czas w UTC, więc konwertujemy go na czas lokalny
        local_tz = tz.gettz("Europe/Warsaw")
        sunrise_local = s['sunrise'].astimezone(local_tz)
        sunset_local = s['sunset'].astimezone(local_tz)

        sunrise = sunrise_local.strftime('%H:%M')
        sunset = sunset_local.strftime('%H:%M')
        return sunrise, sunset
    except Exception as e:
        logging.error(f"Błąd podczas obliczania czasu wschodu/zachodu słońca: {e}")
        return "--:--", "--:--"

# --- Nowy silnik reguł wyboru ikon pogody (zestaw Feather) ---

# Inicjalizujemy słowniki jako None. Zostaną wypełnione przy pierwszym użyciu.
DAY_ICONS = None
NIGHT_ICONS = None

def _initialize_icon_dictionaries():
    """Wypełnia słowniki ikon, gdy ścieżki w config są już dostępne."""
    global DAY_ICONS, NIGHT_ICONS
    # Sprawdź, czy słowniki zostały już zainicjalizowane
    if DAY_ICONS is not None:
        return

    logging.debug("Pierwsze użycie: inicjalizowanie słowników ikon pogody...")
    DAY_ICONS = {
        'clear': os.path.join(config.ICON_FEATHER_PATH, 'sun.svg'),
        'cloudy': os.path.join(config.ICON_FEATHER_PATH, 'cloud.svg'),
        'rain': os.path.join(config.ICON_FEATHER_PATH, 'cloud-rain.svg'),
        'drizzle': os.path.join(config.ICON_FEATHER_PATH, 'cloud-drizzle.svg'),
        'snow': os.path.join(config.ICON_FEATHER_PATH, 'cloud-snow.svg'),
        'storm': os.path.join(config.ICON_FEATHER_PATH, 'cloud-lightning.svg'),
        'fog': os.path.join(config.ICON_FEATHER_PATH, 'align-justify.svg'), # Metafora mgły
    }

    NIGHT_ICONS = {
        'clear': os.path.join(config.ICON_FEATHER_PATH, 'moon.svg'),
        'cloudy': os.path.join(config.ICON_FEATHER_PATH, 'cloud.svg'),
        'rain': os.path.join(config.ICON_FEATHER_PATH, 'cloud-rain.svg'),
        'drizzle': os.path.join(config.ICON_FEATHER_PATH, 'cloud-drizzle.svg'),
        'snow': os.path.join(config.ICON_FEATHER_PATH, 'cloud-snow.svg'),
        'storm': os.path.join(config.ICON_FEATHER_PATH, 'cloud-lightning.svg'),
        'fog': os.path.join(config.ICON_FEATHER_PATH, 'align-justify.svg'),
    }

# Reguły są sprawdzane od góry do dołu. Pierwsza pasująca reguła wyznacza ikonę.
# 'condition' to funkcja lambda, która przyjmuje dane pogodowe i zwraca True/False.
# 'icon_key' to klucz do słowników DAY_ICONS i NIGHT_ICONS.
# Klucze ('zjawisko', 'suma_opadu', 'zachmurzenie_ogolne') są oparte na API IMGW.
WEATHER_RULES = [
    # Zjawiska ekstremalne mają najwyższy priorytet
    {'condition': lambda data: 'burza' in data.get('zjawisko', '').lower(), 'icon_key': 'storm'},
    {'condition': lambda data: 'mgła' in data.get('zjawisko', '').lower(), 'icon_key': 'fog'},

    # Opady
    {'condition': lambda data: 'śnieg' in data.get('zjawisko', '').lower(), 'icon_key': 'snow'},
    {'condition': lambda data: float(data.get('suma_opadu', 0)) > 0.5, 'icon_key': 'rain'},
    {'condition': lambda data: float(data.get('suma_opadu', 0)) > 0, 'icon_key': 'drizzle'},

    # Zachmurzenie (skala 0-8 w API IMGW)
    {'condition': lambda data: float(data.get('zachmurzenie_ogolne', 0)) > 4, 'icon_key': 'cloudy'}, # Zachmurzenie duże lub całkowite

    # Domyślnie - bezchmurnie
    {'condition': lambda data: True, 'icon_key': 'clear'},
]

def _select_weather_icon(weather_api_data, is_day):
    """Wybiera odpowiednią ikonę na podstawie reguł i pory dnia."""
    # Upewnij się, że słowniki ikon są zainicjalizowane
    _initialize_icon_dictionaries()

    for rule in WEATHER_RULES:
        if rule['condition'](weather_api_data):
            icon_key = rule['icon_key']

            # Wybierz zestaw ikon (dzienny/nocny)
            icons_set = DAY_ICONS if is_day else NIGHT_ICONS
            fallback_icons_set = NIGHT_ICONS if is_day else DAY_ICONS

            # Pobierz preferowaną ikonę
            icon_path = icons_set.get(icon_key)

            # Sprawdź, czy plik ikony istnieje
            if icon_path and os.path.exists(icon_path):
                return icon_path

            # Fallback: jeśli ikona dzienna/nocna nie istnieje, spróbuj użyć jej odpowiednika
            fallback_icon_path = fallback_icons_set.get(icon_key)
            if fallback_icon_path and os.path.exists(fallback_icon_path):
                logging.warning(f"Ikona dla klucza '{icon_key}' nie istnieje w preferowanym zestawie. Używam fallback.")
                return fallback_icon_path

            logging.error(f"Nie znaleziono pliku ikony dla klucza '{icon_key}' (ani dziennej, ani nocnej).")

    logging.error("Nie dopasowano żadnej reguły pogodowej. Zwracam ikonę błędu.")
    return config.ICON_SYNC_PROBLEM_PATH

@retry(exceptions=(requests.exceptions.RequestException,), tries=3, delay=5, backoff=2, logger=logging)
def _fetch_imgw_data(url):
    """Pobiera dane z API IMGW z mechanizmem ponawiania prób."""
    logging.info(f"Pobieranie danych pogodowych z API: {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def _get_value_from_airly(airly_data, name):
    """Pomocnicza funkcja do wyciągania wartości z danych Airly."""
    if not airly_data or 'current' not in airly_data or 'values' not in airly_data['current']:
        return None

    for item in airly_data['current']['values']:
        if item['name'] == name:
            return item['value']
    return None

def update_weather_data():
    """
    Łączy dane z dwóch źródeł: dane pomiarowe (temperatura, wilgotność, ciśnienie)
    z Airly (jeśli dostępne), a dane opisowe (zjawiska, zachmurzenie) z IMGW.
    """
    file_path = os.path.join(path_manager.CACHE_DIR, 'weather.json')
    airly_file_path = os.path.join(path_manager.CACHE_DIR, 'airly.json')

    if not hasattr(config, 'IMGW_STATION_NAME') or not config.IMGW_STATION_NAME:
        logging.error("Brak zdefiniowanej nazwy stacji IMGW_STATION_NAME w pliku config.py.")
        # Jeśli nie ma konfiguracji, zapisz plik z danymi zastępczymi, aby uniknąć błędów
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(get_mock_data(), f, ensure_ascii=False, indent=4)
        return

    try:
        # Krok 1: Wczytaj dane z Airly (jeśli istnieją)
        airly_data = None
        try:
            if os.path.exists(airly_file_path):
                with open(airly_file_path, 'r', encoding='utf-8') as f:
                    airly_data = json.load(f)
        except (IOError, json.JSONDecodeError):
            logging.warning(f"Nie można odczytać pliku danych Airly: {airly_file_path}")

        api_url = "https://danepubliczne.imgw.pl/api/data/synop"
        all_stations_data = _fetch_imgw_data(api_url)

        station_data = next((item for item in all_stations_data
                             if item["stacja"].upper() == config.IMGW_STATION_NAME.upper()),
                            None)

        if not station_data:
            # Logujemy błąd, ale nie nadpisujemy starych danych.
            # Jeśli stacja zniknie z API, chcemy zachować ostatnie znane dane.
            logging.error(f"Nie znaleziono danych dla stacji '{config.IMGW_STATION_NAME}' w odpowiedzi z API. Używam danych z cache.")
            return

        # Krok 2: Pomyślnie pobrano dane z IMGW, przetwarzamy je
        sunrise, sunset = _get_sunrise_sunset()

        # Ustal, czy jest dzień, aby wybrać odpowiedni zestaw ikon
        is_day = False
        if sunrise != "--:--" and sunset != "--:--":
            now_time = datetime.now().time()
            sunrise_time = datetime.strptime(sunrise, '%H:%M').time()
            sunset_time = datetime.strptime(sunset, '%H:%M').time()
            if sunrise_time <= now_time < sunset_time:
                is_day = True

        icon_path = _select_weather_icon(station_data, is_day)

        # Krok 3: Połącz dane. Priorytet mają dane z Airly.
        # Jeśli dane z Airly są dostępne, nadpisują te z IMGW.
        temp_real = _get_value_from_airly(airly_data, 'TEMPERATURE') or station_data.get('temperatura')
        humidity = _get_value_from_airly(airly_data, 'HUMIDITY') or station_data.get('wilgotnosc_wzgledna')
        pressure = _get_value_from_airly(airly_data, 'PRESSURE') or station_data.get('cisnienie')

        logging.info(f"Źródło danych pomiarowych: {'Airly' if airly_data and _get_value_from_airly(airly_data, 'TEMPERATURE') is not None else 'IMGW'}")

        data_to_save = {
            "icon": icon_path,
            "temp_real": round(temp_real) if temp_real is not None else '--',
            "sunrise": sunrise,
            "sunset": sunset,
            "humidity": round(humidity) if humidity is not None else '--',
            "pressure": round(pressure) if pressure is not None else '--',
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        logging.info("Pomyślnie zaktualizowano i zapisano dane pogodowe.")

    except requests.exceptions.RequestException as e:
        # W przypadku błędu sieciowego, logujemy ostrzeżenie i celowo NIE robimy nic więcej.
        # Aplikacja automatycznie użyje ostatnich poprawnie zapisanych danych z pliku weather.json.
        logging.warning(f"Błąd sieci podczas pobierania danych pogodowych: {e}. Aplikacja użyje danych z pamięci podręcznej.")

    except Exception as e:
        # W przypadku innych, nieoczekiwanych błędów, również używamy danych z cache.
        logging.error(f"Wystąpił nieoczekiwany błąd w module pogody: {e}. Aplikacja użyje danych z pamięci podręcznej.", exc_info=True)
