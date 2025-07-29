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
        "icon": config.DEFAULT_WEATHER_ICON_PATH,
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

# --- Nowa, oparta na regułach struktura do mapowania pogody na ikony ---
# Lista reguł jest oceniana od góry do dołu. Pierwsza pasująca reguła określa ikonę.
# Każda reguła to krotka: (lambda warunku, podstawowa nazwa ikony).
# Lambda otrzymuje słownik station_data i powinna zwrócić True, jeśli warunek jest spełniony.
# Podstawowa nazwa ikony to rdzeń nazwy pliku, bez prefiksu dnia/nocy i rozszerzenia.
WEATHER_RULES = [
    # --- Reguły dla opadów (najwyższy priorytet) ---
    # TODO: Można tu dodać bardziej szczegółowe reguły (np. dla mgły, burzy), jeśli API dostarczy odpowiednie dane.
    (lambda d: float(d.get('suma_opadu', 0)) > 0 and float(d.get('temperatura', 1)) <= 0, 'n3z70'),  # Duże opady śniegu
    (lambda d: float(d.get('suma_opadu', 0)) > 0, 'n2z70'),                                          # Duży deszcz (domyślne dla innych opadów)

    # --- Reguły dla zachmurzenia (gdy brak opadów) ---
    (lambda d: float(d.get('zachmurzenie_ogolne', 8)) <= 2, 'n0z00'),                                # Bezchmurnie
    (lambda d: float(d.get('zachmurzenie_ogolne', 8)) <= 5, 'n0z50'),                                # Częściowe zachmurzenie
    (lambda d: float(d.get('zachmurzenie_ogolne', 8)) <= 7, 'n0z70'),                                # Zachmurzenie duże

    # --- Reguła domyślna ---
    (lambda d: True, 'n0z80'),                                                                      # Całkowite zachmurzenie (domyślne)
]

def _map_weather_to_icon(station_data):
    """
    Mapuje dane ze stacji na odpowiednią nazwę pliku ikony, używając systemu opartego na regułach.
    Poprawnie obsługuje rozróżnienie ikon dziennych i nocnych.
    """
    fallback_icon_path = config.DEFAULT_WEATHER_ICON_PATH

    try:
        # --- Krok 1: Ustal, czy jest dzień czy noc, aby wybrać poprawny prefiks ikony ---
        sunrise_str, sunset_str = _get_sunrise_sunset()
        is_day = False
        if sunrise_str != "--:--" and sunset_str != "--:--":
            now = datetime.now().time()
            sunrise_time = datetime.strptime(sunrise_str, '%H:%M').time()
            sunset_time = datetime.strptime(sunset_str, '%H:%M').time()
            if sunrise_time <= now < sunset_time:
                is_day = True
        prefix = 'd' if is_day else 'n'
        alt_prefix = 'n' if is_day else 'd'

        # --- Krok 2: Znajdź pasujący kod ikony za pomocą silnika reguł ---
        icon_base_code = None
        for condition, code in WEATHER_RULES:
            if condition(station_data):
                icon_base_code = code
                break

        # --- Krok 3: Zbuduj ścieżkę i sprawdź, czy plik istnieje (z opcją awaryjną) ---
        primary_icon_path = os.path.join('imgw', prefix, f"{icon_base_code}.svg")
        full_primary_path = os.path.join(config.WEATHER_ICONS_PATH, primary_icon_path)

        if os.path.exists(full_primary_path):
            return full_primary_path

        # Jeśli preferowana ikona (np. dzienna) nie istnieje, spróbuj alternatywnej (np. nocnej)
        alt_icon_path = os.path.join('imgw', alt_prefix, f"{icon_base_code}.svg")
        full_alt_path = os.path.join(config.WEATHER_ICONS_PATH, alt_icon_path)
        if os.path.exists(full_alt_path):
            logging.debug(f"Ikona '{primary_icon_path}' nie istnieje, używam alternatywnej '{alt_icon_path}'.")
            return full_alt_path

        logging.warning(f"Nie znaleziono ani preferowanej ('{primary_icon_path}') ani alternatywnej ikony. Używam ikony zastępczej.")
        return fallback_icon_path

    except (ValueError, TypeError, AttributeError) as e:
        logging.error(f"Błąd podczas mapowania ikony pogody: {e}. Używam ikony zastępczej.")
        return fallback_icon_path

@retry(exceptions=(requests.exceptions.RequestException,), tries=3, delay=5, backoff=2, logger=logging)
def _fetch_imgw_data(url):
    """Pobiera dane z API IMGW z mechanizmem ponawiania prób."""
    logging.info(f"Pobieranie danych pogodowych z API: {url}")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def update_weather_data():
    """
    Pobiera dane pogodowe z API IMGW. W przypadku błędu sieciowego,
    aplikacja będzie korzystać z ostatnich pomyślnie pobranych danych (cache).
    Nowe dane są zapisywane do pliku JSON tylko po pomyślnym pobraniu.
    """
    file_path = os.path.join(path_manager.CACHE_DIR, 'weather.json')

    if not hasattr(config, 'IMGW_STATION_NAME') or not config.IMGW_STATION_NAME:
        logging.error("Brak zdefiniowanej nazwy stacji IMGW_STATION_NAME w pliku config.py.")
        # Jeśli nie ma konfiguracji, zapisz plik z danymi zastępczymi, aby uniknąć błędów
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(get_mock_data(), f, ensure_ascii=False, indent=4)
        return

    try:
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

        # --- Pomyślnie pobrano dane, przetwarzamy i zapisujemy ---
        icon_path = _map_weather_to_icon(station_data)
        sunrise, sunset = _get_sunrise_sunset()

        data_to_save = {
            "icon": icon_path,
            "temp_real": station_data.get('temperatura'),
            "sunrise": sunrise,
            "sunset": sunset,
            "humidity": station_data.get('wilgotnosc_wzgledna'),
            "pressure": station_data.get('cisnienie'),
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
