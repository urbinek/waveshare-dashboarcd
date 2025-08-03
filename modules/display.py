import logging
import os
import json
import sys
import textwrap
import random
import threading
from PIL import Image, ImageDraw, ImageChops
from filelock import FileLock

from modules.config_loader import config
from modules import path_manager, drawing_utils, asset_manager
from modules.panels import time_panel, weather_panel, events_panel, calendar_panel

from waveshare_epd import epd7in5b_V2

EPD_WIDTH = epd7in5b_V2.EPD_WIDTH
EPD_HEIGHT = epd7in5b_V2.EPD_HEIGHT

IMAGE_BLACK_PATH = os.path.join(path_manager.CACHE_DIR, 'image_black.png')
IMAGE_RED_PATH = os.path.join(path_manager.CACHE_DIR, 'image_red.png')
IMAGE_LOCK_PATH = os.path.join(path_manager.CACHE_DIR, 'image.lock')

EPD_LOCK = threading.Lock()
_FLIP_LOGGED = False

def _shift_image(image, dx, dy):
    """Przesuwa obraz o (dx, dy) pikseli, wypełniając tło białym kolorem."""
    shifted_image = Image.new(image.mode, image.size, 255)
    shifted_image.paste(image, (dx, dy))
    return shifted_image

def safe_read_json(file_name, default_data=None):
    """Bezpiecznie wczytuje dane z pliku JSON."""
    if default_data is None:
        default_data = {}
    file_path = os.path.join(path_manager.CACHE_DIR, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logging.warning(f"Nie można odczytać pliku {file_path}: {e}. Używam danych domyślnych.")
        return default_data

def generate_image(layout_config, draw_borders=False):
    """Generuje obraz do wyświetlenia na podstawie danych z plików JSON."""
    time_data = safe_read_json('time.json', {'time': '??:??', 'date': 'Brak daty', 'weekday': 'Brak dnia'})
    weather_data = safe_read_json('weather.json', {
        'icon': asset_manager.get_path('icon_sync_problem'),
        'temp_real': '??', 'sunrise': '--:--', 'sunset': '--:--',
        'humidity': '--', 'pressure': '--'
    })
    airly_data = safe_read_json('airly.json', {
        "current": {"indexes": [{"name": "AIRLY_CAQI", "value": 0, "level": "UNKNOWN", "description": "Brak danych"}]}
    })
    calendar_data = safe_read_json('calendar.json', {
        'upcoming_events': [],
        'unusual_holiday': '', 'unusual_holiday_desc': '',
        'month_calendar': []
    })

    black_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)
    red_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)
    draw_black = ImageDraw.Draw(black_image)
    draw_red = ImageDraw.Draw(red_image)

    fonts = drawing_utils.load_fonts()

    if layout_config.get('time', {}).get('enabled', True):
        time_panel.draw_panel(black_image, draw_black, time_data, weather_data, fonts, layout_config['time'])
    else:
        logging.info("Panel 'time' jest wyłączony w konfiguracji. Pomijanie.")

    if layout_config.get('weather_and_air', {}).get('enabled', True):
        weather_panel.draw_panel(black_image, draw_red, weather_data, airly_data, fonts, layout_config['weather_and_air'])
    else:
        logging.info("Panel 'weather_and_air' jest wyłączony w konfiguracji. Pomijanie.")

    if calendar_data.get('error') == 'AUTH_ERROR':
        error_message = "Błąd autoryzacji Kalendarza Google. Uruchom skrypt `modules/google_calendar.py` ręcznie."
        if layout_config.get('calendar', {}).get('enabled', True):
            drawing_utils.draw_error_message(draw_red, error_message, fonts, layout_config['calendar'])
        if layout_config.get('events', {}).get('enabled', True):
            drawing_utils.draw_error_message(draw_black, error_message, fonts, layout_config['events'])
    else:
        if layout_config.get('events', {}).get('enabled', True):
            events_panel.draw_panel(draw_black, draw_red, calendar_data, fonts, layout_config['events'])
        if layout_config.get('calendar', {}).get('enabled', True):
            calendar_panel.draw_panel(draw_black, draw_red, calendar_data, fonts, layout_config['calendar'])

    if draw_borders:
        logging.info("Rysowanie granic paneli (tryb deweloperski).")
        for panel_name, panel_config in layout_config.items():
            if panel_config.get('enabled', True) and 'rect' in panel_config:
                draw_black.rectangle(panel_config['rect'], outline=0)

    unusual_holiday_title = calendar_data.get('unusual_holiday', '')
    unusual_holiday_desc = calendar_data.get('unusual_holiday_desc', '')

    if unusual_holiday_title and "Brak nietypowych świąt" not in unusual_holiday_title:
        logging.debug(f"Rysowanie nietypowego święta: '{unusual_holiday_title}'")
        font_title = fonts.get('small_bold')
        font_desc = fonts.get('small')
        y_start_area = 400
        area_height = EPD_HEIGHT - y_start_area
        y_center_area = y_start_area + area_height // 2
        max_width_chars_title = 45
        max_width_chars_desc = 55
        wrapped_title = textwrap.wrap(unusual_holiday_title, width=max_width_chars_title)
        title_line_height = font_title.getbbox("A")[3] - font_title.getbbox("A")[1] + 5
        total_title_height = len(wrapped_title) * title_line_height
        wrapped_desc = []
        total_desc_height = 0
        if unusual_holiday_desc:
            wrapped_desc = textwrap.wrap(unusual_holiday_desc, width=max_width_chars_desc)
            desc_line_height = font_desc.getbbox("A")[3] - font_desc.getbbox("A")[1] + 4
            total_desc_height = len(wrapped_desc) * desc_line_height + 5
        total_block_height = total_title_height + total_desc_height
        current_y = y_center_area - total_block_height // 2 + 10
        for line in wrapped_title:
            draw_black.text((EPD_WIDTH // 2, current_y), line, font=font_title, fill=0, anchor="mt")
            current_y += title_line_height
        if wrapped_desc:
            current_y += 5
            for line in wrapped_desc:
                draw_black.text((EPD_WIDTH // 2, current_y), line, font=font_desc, fill=0, anchor="mt")
                current_y += desc_line_height
    return black_image, red_image

def _execute_display_update(black_img, red_img, mode, flip, clear_screen=False):
    """
    Prywatna funkcja pomocnicza do obsługi komunikacji z wyświetlaczem E-Ink.
    """
    global _FLIP_LOGGED
    try:
        with EPD_LOCK:
            log_level = logging.DEBUG if mode == 'fast' else logging.INFO
            logging.log(log_level, f"Rozpoczynanie aktualizacji wyświetlacza (tryb: {mode}).")
            if flip:
                if not _FLIP_LOGGED:
                    logging.info("Obracanie obrazu o 180 stopni.")
                    _FLIP_LOGGED = True
                else:
                    logging.debug("Obracanie obrazu o 180 stopni.")
                black_img_display = black_img.rotate(180)
                red_img_display = red_img.rotate(180)
            else:
                black_img_display = black_img
                red_img_display = red_img
            epd = epd7in5b_V2.EPD()
            if mode == 'full':
                epd.init()
                if clear_screen:
                    logging.debug("Czyszczenie ekranu przed pełnym odświeżeniem.")
                    epd.Clear()
            elif mode == 'fast':
                epd.init_Fast()
            else:
                raise ValueError(f"Nieznany tryb aktualizacji: {mode}")
            epd.display(epd.getbuffer(black_img_display), epd.getbuffer(red_img_display))
            epd.sleep()
            logging.log(log_level, f"Aktualizacja wyświetlacza (tryb: {mode}) zakończona.")
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas komunikacji z wyświetlaczem: {e}", exc_info=True)

def update_display(layout_config, force_full_refresh=False, draw_borders=False, apply_pixel_shift=False, flip=False):
    """Generuje nowy obraz i wykonuje pełne odświeżenie wyświetlacza."""
    try:
        logging.info("Generowanie nowego obrazu do pełnego odświeżenia.")
        black_img, red_img = generate_image(layout_config, draw_borders=draw_borders)
        if apply_pixel_shift:
            max_shift = 2
            dx = random.randint(-max_shift, max_shift)
            dy = random.randint(-max_shift, max_shift)
            logging.info(f"Stosowanie przesunięcia pikseli o ({dx}, {dy}) w celu ochrony ekranu.")
            black_img = _shift_image(black_img, dx, dy)
            red_img = _shift_image(red_img, dx, dy)
        with FileLock(IMAGE_LOCK_PATH):
            black_img.save(IMAGE_BLACK_PATH, "PNG")
            red_img.save(IMAGE_RED_PATH, "PNG")
        _execute_display_update(black_img, red_img, mode='full', flip=flip, clear_screen=force_full_refresh)
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas przygotowywania pełnej aktualizacji: {e}", exc_info=True)

def partial_update_time(layout_config, draw_borders=False, flip=False):
    """Aktualizuje tylko panel czasu na ekranie, używając szybkiego odświeżenia."""
    time_panel_config = layout_config.get('time', {})
    if not time_panel_config or not time_panel_config.get('enabled', True):
        logging.debug("Panel czasu jest wyłączony w konfiguracji, pomijam częściową aktualizację.")
        return
    try:
        with FileLock(IMAGE_LOCK_PATH):
            if not os.path.exists(IMAGE_BLACK_PATH) or not os.path.exists(IMAGE_RED_PATH):
                logging.error("Brak zapisanych obrazów cache. Nie można wykonać częściowej aktualizacji.")
                return
            black_image = Image.open(IMAGE_BLACK_PATH)
            red_image = Image.open(IMAGE_RED_PATH)
        draw_black = ImageDraw.Draw(black_image)
        fonts = drawing_utils.load_fonts()
        time_data = safe_read_json('time.json')
        weather_data = safe_read_json('weather.json')
        draw_black.rectangle(time_panel_config['rect'], fill=255)
        time_panel.draw_panel(black_image, draw_black, time_data, weather_data, fonts, time_panel_config)
        if draw_borders:
            draw_black.rectangle(time_panel_config['rect'], outline=0)
        with FileLock(IMAGE_LOCK_PATH):
            black_image.save(IMAGE_BLACK_PATH, "PNG")
        _execute_display_update(black_image, red_image, mode='fast', flip=flip)
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas przygotowywania częściowej aktualizacji: {e}", exc_info=True)

def clear_display():
    """Inicjalizuje wyświetlacz i czyści jego zawartość."""
    try:
        with EPD_LOCK:
            logging.info("Czyszczenie wyświetlacza e-ink...")
            epd = epd7in5b_V2.EPD()
            epd.init()
            epd.Clear()
            epd.sleep()
            logging.info("Wyświetlacz wyczyszczony.")
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas czyszczenia wyświetlacza: {e}", exc_info=True)