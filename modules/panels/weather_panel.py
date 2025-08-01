import logging
from datetime import datetime, timezone
from PIL import Image
from dateutil import parser
import textwrap

from modules import drawing_utils
import config

# Zmienna globalna do śledzenia ostatnio użytej ikony pogody
_last_weather_icon_path = None

def _get_caqi_data(airly_data):
    """Pomocnicza funkcja do wyciągania danych CAQI z odpowiedzi Airly."""
    if not airly_data or 'current' not in airly_data or 'indexes' not in airly_data['current']:
        return None

    for index in airly_data['current']['indexes']:
        if index.get('name') == 'AIRLY_CAQI':
            return {
                'value': round(index.get('value', 0)),
                'level': index.get('level', 'UNKNOWN').replace('_', ' ').title(),
                'description': index.get('description', 'Brak danych'),
                'advice': index.get('advice', 'Brak porad.'),
                'color_name': index.get('level', 'UNKNOWN')
            }
    return None

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

def draw_panel(black_image, draw_red, weather_data, airly_data, fonts, panel_config):
    """Rysuje zintegrowany panel pogody i jakości powietrza."""
    global _last_weather_icon_path

    rect = panel_config.get('rect', [0, 0, 0, 0])
    x1, y1, x2, y2 = rect
    panel_width = x2 - x1

    # --- 1. Ekstrakcja danych ---
    icon_path = weather_data.get('icon')
    temp_text = f"{weather_data.get('temp_real', '--')}°"
    humidity_text = f"{weather_data.get('humidity', '--')}%"
    pressure_text = f"{weather_data.get('pressure', '--')} hPa"

    caqi_data = _get_caqi_data(airly_data)
    if caqi_data:
        caqi_text = str(caqi_data['value'])
        advice_text = caqi_data['advice']
    else:
        caqi_text = "--"
        advice_text = ""

    # --- 2. Logowanie zmiany ikony ---
    if icon_path and icon_path != _last_weather_icon_path:
        logging.info(f"Zmiana ikony pogody. Nowa ikona: {icon_path}")
        _last_weather_icon_path = icon_path

    # --- 3. Rysowanie Linii 1: Ikona + Temperatura ---
    line1_y_center = y1 + 45
    icon_img = drawing_utils.render_svg_with_cache(icon_path, size=80) if icon_path else None
    temp_font = fonts['weather_temp']

    gap_between_elements = 20
    icon_width = icon_img.width if icon_img else 0
    temp_width = draw_red.textlength(temp_text, font=temp_font)
    total_content_width = icon_width + gap_between_elements + temp_width
    content_start_x = x1 + (panel_width - total_content_width) // 2

    current_x = content_start_x
    if icon_img:
        icon_y = line1_y_center - icon_img.height // 2
        black_image.paste(icon_img, (int(current_x), icon_y), mask=icon_img)
        current_x += icon_width + gap_between_elements

    # Rysujemy temperaturę na czerwono
    draw_red.text((current_x, line1_y_center), temp_text, font=temp_font, fill=0, anchor="lm")

    # --- 4. Rysowanie Linii 2: Wilgotność, Ciśnienie, Jakość Powietrza ---
    small_font = fonts['small']
    # Zwiększamy rozmiar ikon o ~30% (z 24 na 32)
    icon_size = 32
    line2_y = y1 + 100 # Przesunięte w dół, aby uniknąć kolizji z ikoną pogody
    icon_text_gap = 5

    # Przygotuj dane i ikony dla każdego bloku
    blocks = []
    if config.ICON_HUMIDITY_PATH:
        humidity_icon = drawing_utils.render_svg_with_cache(config.ICON_HUMIDITY_PATH, size=icon_size)
        if humidity_icon:
            width = humidity_icon.width + icon_text_gap + draw_red.textlength(humidity_text, font=small_font)
            blocks.append({'icon': humidity_icon, 'text': humidity_text, 'width': width})

    if config.ICON_PRESSURE_PATH:
        pressure_icon = drawing_utils.render_svg_with_cache(config.ICON_PRESSURE_PATH, size=icon_size)
        if pressure_icon:
            width = pressure_icon.width + icon_text_gap + draw_red.textlength(pressure_text, font=small_font)
            blocks.append({'icon': pressure_icon, 'text': pressure_text, 'width': width})

    if caqi_data and config.ICON_AIR_QUALITY_PATH:
        air_quality_icon = drawing_utils.render_svg_with_cache(config.ICON_AIR_QUALITY_PATH, size=icon_size)
        if air_quality_icon:
            width = air_quality_icon.width + icon_text_gap + draw_red.textlength(caqi_text, font=small_font)
            blocks.append({'icon': air_quality_icon, 'text': caqi_text, 'width': width})

    # Oblicz równe odstępy i rysuj bloki
    if blocks:
        total_blocks_width = sum(b['width'] for b in blocks)
        # Mamy n bloków i n+1 odstępów (wliczając marginesy po bokach)
        space_for_gaps = panel_width - total_blocks_width
        gap_size = space_for_gaps / (len(blocks) + 1)

        current_x = x1 + gap_size
        for block in blocks:
            # Rysuj ikonę
            icon_y = int(line2_y - block['icon'].height // 2)
            black_image.paste(block['icon'], (int(current_x), icon_y), mask=block['icon'])
            current_x += block['icon'].width + icon_text_gap

            # Rysuj tekst
            draw_red.text((current_x, line2_y), block['text'], font=small_font, fill=0, anchor="lm")
            current_x += draw_red.textlength(block['text'], font=small_font) + gap_size

    # --- 5. Rysowanie Linii 3: Porada (Advice) ---
    line3_y = y1 + 125
    if advice_text:
        wrapped_advice = textwrap.wrap(advice_text, width=40)
        for i, line in enumerate(wrapped_advice):
            draw_red.text((x1 + panel_width // 2, line3_y + i * 20), line, font=small_font, fill=0, anchor="mt", align="center")

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
