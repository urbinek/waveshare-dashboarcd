import logging
from datetime import datetime, timezone
from PIL import Image
from dateutil import parser

from modules import drawing_utils
import config

def _format_timedelta_human(delta):
    """
    Formatuje obiekt timedelta na czytelny dla człowieka ciąg znaków, np. '2h temu'.
    """
    seconds = delta.total_seconds()

    # Mniej niż 2 minuty traktujemy jako "przed chwilą"
    if seconds < 120:
        return "przed chwilą"

    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes}m temu"

    hours = round(minutes / 60)
    if hours < 24:
        return f"{hours}h temu"

    days = round(hours / 24)
    return f"{days}d temu"

def draw_panel(black_image, draw_black, weather_data, fonts, panel_config):
    """Rysuje panel pogody, w tym wskaźnik wieku danych, jeśli są nieaktualne."""
    rect = panel_config.get('rect', [0, 0, 0, 0])
    x1, y1, x2, y2 = rect
    y_offset = panel_config.get('y_offset', 0)
    y1 += y_offset
    y2 += y_offset

    # --- Definicja obszarów ---
    # Dzielimy panel na górny obszar (ikona + temperatura) i dolny (wilgotność, ciśnienie).
    bottom_area_height = 40  # Zmniejszono, aby dać więcej miejsca na ikonę
    top_area_y1 = y1
    top_area_y2 = y2 - bottom_area_height
    top_area_center_y = top_area_y1 + (top_area_y2 - top_area_y1) // 2

    # --- Górny obszar: Ikona i Temperatura (traktowane jako jeden blok) ---

    # 1. Pobierz zasoby i oblicz ich wymiary
    icon_path = weather_data.get('icon')
    icon_img = drawing_utils.render_svg_with_cache(icon_path, size=144) if icon_path else None # Powiększono ikonę o 20%
    temp_text = f"{weather_data.get('temp_real', '--')}°"
    temp_font = fonts['weather_temp']

    # 2. Oblicz łączną szerokość bloku, aby wycentrować go w poziomie
    gap_between_elements = -30
    icon_width = icon_img.width if icon_img else 0
    temp_width = draw_black.textlength(temp_text, font=temp_font)
    total_content_width = icon_width + gap_between_elements + temp_width
    content_start_x = x1 + ((x2 - x1) - total_content_width) // 2

    # 3. Rysuj elementy, wyrównując je w pionie do środka obszaru
    current_x = content_start_x
    if icon_img:
        icon_y = top_area_center_y - icon_img.height // 2
        # Użycie kanału alfa obrazu jako maski pozwoli na dithering (skalę szarości).
        # To przywraca detale w ikonach kosztem nieco jaśniejszego wyglądu.
        black_image.paste(icon_img, (int(current_x), icon_y), mask=icon_img)
        current_x += icon_width + gap_between_elements

    # Użycie anchor="lm" (left-middle) zapewnia idealne wyrównanie pionowe tekstu
    draw_black.text((current_x, top_area_center_y), temp_text, font=temp_font, fill=0, anchor="lm")

    # --- Rysowanie wilgotności i ciśnienia w jednej linii z ikonami ---
    icon_size = 36  # Zwiększono z 24
    text_y_pos = top_area_y2 + (bottom_area_height // 2) # Wyśrodkowanie w dolnym obszarze

    # --- Centrowanie bloku wilgotności i ciśnienia ---
    humidity_icon = drawing_utils.render_svg_with_cache(config.ICON_HUMIDITY_PATH, size=icon_size)
    humidity_text = f"{weather_data.get('humidity', '--')}%"
    pressure_icon = drawing_utils.render_svg_with_cache(config.ICON_PRESSURE_PATH, size=icon_size)
    pressure_text = f"{weather_data.get('pressure', '--')} hPa"

    # Obliczanie całkowitej szerokości bloku
    total_width = 0
    padding_between_items = 25
    icon_text_gap = 5

    if humidity_icon:
        total_width += humidity_icon.width + icon_text_gap
    total_width += draw_black.textlength(humidity_text, font=fonts['small'])
    total_width += padding_between_items
    if pressure_icon:
        total_width += pressure_icon.width + icon_text_gap
    total_width += draw_black.textlength(pressure_text, font=fonts['small'])

    # Obliczanie pozycji startowej X, aby wycentrować blok w całym panelu
    panel_width = x2 - x1
    start_x = x1 + (panel_width - total_width) // 2
    current_x = start_x

    # Wilgotność
    if humidity_icon:
        # Wklejenie ikony z użyciem jej własnego kanału alfa jako maski
        black_image.paste(humidity_icon, (int(current_x), int(text_y_pos - icon_size // 2)), mask=humidity_icon)
        current_x += humidity_icon.width + icon_text_gap
    draw_black.text((current_x, text_y_pos), humidity_text, font=fonts['small'], fill=0, anchor="lm")
    current_x += draw_black.textlength(humidity_text, font=fonts['small']) + padding_between_items

    # Ciśnienie
    if pressure_icon:
        # Wklejenie ikony z użyciem jej własnego kanału alfa jako maski
        black_image.paste(pressure_icon, (int(current_x), int(text_y_pos - icon_size // 2)), mask=pressure_icon)
        current_x += pressure_icon.width + icon_text_gap
    draw_black.text((current_x, text_y_pos), pressure_text, font=fonts['small'], fill=0, anchor="lm")

    # --- Wskaźnik nieaktualnych danych ---
    timestamp_str = weather_data.get('timestamp')
    if timestamp_str:
        try:
            data_time = parser.isoparse(timestamp_str)
            age = datetime.now(timezone.utc) - data_time

            # Wyświetlaj wskaźnik, jeśli dane są starsze niż 65 minut
            if age.total_seconds() > 60 * 65:
                logging.info(f"Dane pogodowe są nieaktualne ({_format_timedelta_human(age)}). Wyświetlam ikonę ostrzegawczą.")

                # Renderuj i rysuj ikonę problemu z synchronizacją
                sync_icon_size = 30
                sync_icon = drawing_utils.render_svg_with_cache(config.ICON_SYNC_PROBLEM_PATH, size=sync_icon_size)
                icon_pos_x = x2 - sync_icon.width - 15
                icon_pos_y = y1 + 15
                # Wklejenie ikony z użyciem jej własnego kanału alfa jako maski
                black_image.paste(sync_icon, (icon_pos_x, icon_pos_y), mask=sync_icon)
        except (parser.ParserError, TypeError) as e:
            logging.warning(f"Nie można sparsować znacznika czasu danych pogodowych ('{timestamp_str}'): {e}")
