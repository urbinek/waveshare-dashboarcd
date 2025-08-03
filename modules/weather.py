import os
import json
import logging
from datetime import date, datetime, timezone
from astral.sun import sun
from astral import LocationInfo
from dateutil import tz

from modules.config_loader import config
from modules import path_manager, asset_manager

WEATHER_ICON_MAP = {
    1: 'sun', 2: 'sun', 3: 'sun', 4: 'sun', 5: 'sun', 6: 'cloud', 7: 'cloud', 8: 'cloud',
    11: 'align-justify', 12: 'cloud-rain', 13: 'cloud-rain', 14: 'cloud-rain', 15: 'cloud-lightning',
    16: 'cloud-lightning', 17: 'cloud-lightning', 18: 'cloud-rain', 19: 'cloud-snow', 20: 'cloud-snow',
    21: 'cloud-snow', 22: 'cloud-snow', 23: 'cloud-snow', 24: 'cloud-snow', 25: 'cloud-drizzle',
    26: 'cloud-drizzle', 29: 'cloud-snow', 30: 'thermometer', 31: 'wind', 32: 'wind',
    33: 'moon', 34: 'moon', 35: 'cloud', 36: 'cloud', 37: 'cloud', 38: 'cloud',
    39: 'cloud-rain', 40: 'cloud-rain', 41: 'cloud-lightning', 42: 'cloud-lightning',
    43: 'cloud-snow', 44: 'cloud-snow'
}

def _select_weather_icon(icon_number):
    """Wybiera ikonę Feather na podstawie numeru ikony z AccuWeather."""
    if icon_number is None:
        return asset_manager.get_path('icon_sync_problem')
    icon_name = WEATHER_ICON_MAP.get(icon_number, 'alert-triangle')
    return os.path.join(asset_manager.get_path('icons_feather_path'), f'{icon_name}.svg')

def _get_sunrise_sunset():
    """Oblicza czas wschodu i zachodu słońca."""
    try:
        location_config = config['location']
        loc = LocationInfo("Warsaw", "Poland", "Europe/Warsaw", location_config['latitude'], location_config['longitude'])
        s = sun(loc.observer, date=date.today())
        local_tz = tz.gettz("Europe/Warsaw")
        sunrise = s['sunrise'].astimezone(local_tz).strftime('%H:%M')
        sunset = s['sunset'].astimezone(local_tz).strftime('%H:%M')
        return sunrise, sunset
    except Exception as e:
        logging.error(f"Błąd podczas obliczania czasu wschodu/zachodu słońca: {e}")
        return "--:--", "--:--"

def update_weather_data():
    """Tworzy ujednolicony plik weather.json z danych Airly i AccuWeather."""
    airly_file_path = os.path.join(path_manager.CACHE_DIR, 'airly.json')
    airly_data = {}
    temp_real, humidity, pressure = "--", "--", "--"

    try:
        with open(airly_file_path, 'r', encoding='utf-8') as f:
            airly_data = json.load(f)
        
        values = {item['name']: item['value'] for item in airly_data.get('current', {}).get('values', [])}
        temp_real = round(values.get('TEMPERATURE', 0))
        humidity = round(values.get('HUMIDITY', 0))
        pressure = round(values.get('PRESSURE', 0))

    except (IOError, json.JSONDecodeError, TypeError) as e:
        logging.warning(f"Nie można odczytać lub przetworzyć pliku Airly: {e}.")

    accuweather_file_path = os.path.join(path_manager.CACHE_DIR, 'accuweather.json')
    accuweather_data = {}
    current_icon_num, forecast_icon_num = None, None

    try:
        with open(accuweather_file_path, 'r', encoding='utf-8') as f:
            accuweather_data = json.load(f)
        
        current_icon_num = accuweather_data.get('current', {}).get('WeatherIcon')
        forecast_icon_num = accuweather_data.get('forecast', {}).get('Day', {}).get('Icon')

    except (IOError, json.JSONDecodeError) as e:
        logging.info(f"Plik AccuWeather nie jest dostępny: {e}.")

    sunrise, sunset = _get_sunrise_sunset()

    final_weather_data = {
        "icon": _select_weather_icon(current_icon_num),
        "forecast_icon": _select_weather_icon(forecast_icon_num),
        "temp_real": temp_real,
        "humidity": humidity,
        "pressure": pressure,
        "sunrise": sunrise,
        "sunset": sunset,
        "cloud_cover": accuweather_data.get('current', {}).get('CloudCover', 0),
        "forecast_temp_min": round(accuweather_data.get('forecast', {}).get('Temperature', {}).get('Minimum', {}).get('Value', 0)) if accuweather_data else '--',
        "forecast_temp_max": round(accuweather_data.get('forecast', {}).get('Temperature', {}).get('Maximum', {}).get('Value', 0)) if accuweather_data else '--',
        "timestamp": datetime.now(tz=timezone.utc).isoformat()
    }
    
    output_file_path = os.path.join(path_manager.CACHE_DIR, 'weather.json')
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_weather_data, f, ensure_ascii=False, indent=4)
        logging.info("Pomyślnie zintegrowano dane z Airly i AccuWeather do weather.json.")
    except IOError as e:
        logging.error(f"Nie można zapisać finalnego pliku weather.json: {e}")