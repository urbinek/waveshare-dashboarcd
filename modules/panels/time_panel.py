import logging
import os
from PIL import Image
import config
from modules import drawing_utils

def _draw_sun_info(image, draw, icon, text, font, center_x, y_pos):
    """Pomocnicza funkcja do rysowania bloku ikona + tekst (dla wschodu/zachodu słońca)."""
    if not icon: return

    text_w = int(draw.textlength(text, font=font))
    total_w = icon.width + 5 + text_w
    start_x = center_x - (total_w // 2)

    # Oblicz pozycję Y dla ikony, aby była wycentrowana z tekstem
    icon_y = int(y_pos - icon.height // 2)

    image.paste(icon, (int(start_x), int(icon_y)), icon if icon.mode == 'RGBA' else None)
    draw.text((start_x + icon.width + 5, y_pos), text, font=font, fill=0, anchor="lm")

def draw_panel(black_image, draw_black, time_data, weather_data, fonts, box_info):
    """Rysuje panel czasu z podziałem na datę i informacje o słońcu."""
    logging.debug(f"Rysowanie panelu czasu w obszarze: {box_info['rect']}")
    rect = box_info['rect']
    y_offset = box_info.get('y_offset', 0)
    box_center_x = rect[0] + (rect[2] - rect[0]) // 2
    box_width = rect[2] - rect[0]

    time_str = time_data.get('time', '??:??')
    weekday_str = time_data.get('weekday', 'Brak dnia')
    date_str = time_data.get('date', 'Brak daty')

    # --- Ustawienia i czcionki ---
    font_large = fonts['large']
    font_medium = fonts['medium']
    font_small = fonts['small']
    padding = 10
    # Podział na dwie kolumny: data i słońce
    date_col_width = int(box_width * 0.60)
    sun_col_width = box_width - date_col_width

    # --- Przygotowanie danych i ikon słońca ---
    sunrise_str = weather_data.get('sunrise', '--:--')
    sunset_str = weather_data.get('sunset', '--:--')
    sun_icon_size = 36

    sunrise_icon = drawing_utils.render_svg_with_cache(config.ICON_SUNRISE_PATH, size=sun_icon_size)
    sunset_icon = drawing_utils.render_svg_with_cache(config.ICON_SUNSET_PATH, size=sun_icon_size)

    # --- Obliczenia wysokości do centrowania pionowego ---
    time_h = font_large.getmask(time_str).size[1]
    date_col_h = font_medium.getmask(weekday_str).size[1] + 5 + font_medium.getmask(date_str).size[1]
    sun_col_h = sun_icon_size * 2 # Przybliżona wysokość dla dwóch ikon słońca
    bottom_part_h = max(date_col_h, sun_col_h)

    total_height = time_h + padding + bottom_part_h
    box_height = rect[3] - rect[1]
    y_start = rect[1] + (box_height - total_height) // 2 + y_offset

    # --- Rysowanie ---
    # 1. Zegar (na całej szerokości)
    current_y = y_start
    draw_black.text((box_center_x, current_y), time_str, font=font_large, fill=0, anchor="mt")
    current_y += time_h + padding

    # 2. Lewa kolumna (data)
    date_col_center_x = rect[0] + (date_col_width // 2)
    draw_black.text((date_col_center_x, current_y), weekday_str, font=font_medium, fill=0, anchor="mt")
    weekday_h = font_medium.getmask(weekday_str).size[1]
    draw_black.text((date_col_center_x, current_y + weekday_h + 5), date_str, font=font_medium, fill=0, anchor="mt")

    # 3. Prawa kolumna (słońce)
    sun_col_start_x = rect[0] + date_col_width
    sun_col_center_x = sun_col_start_x + (sun_col_width // 2)
    sun_info_y_center = current_y + (bottom_part_h // 2)

    # Oblicz pozycje Y dla wschodu i zachodu, aby były symetrycznie wokół środka
    sunrise_y_pos = sun_info_y_center - (sun_icon_size // 2)
    sunset_y_pos = sun_info_y_center + (sun_icon_size // 2)

    # Rysowanie wschodu i zachodu słońca za pomocą funkcji pomocniczej
    if sunrise_icon:
        _draw_sun_info(black_image, draw_black, sunrise_icon, sunrise_str, font_small, sun_col_center_x, sunrise_y_pos)

    if sunset_icon:
        _draw_sun_info(black_image, draw_black, sunset_icon, sunset_str, font_small, sun_col_center_x, sunset_y_pos)
