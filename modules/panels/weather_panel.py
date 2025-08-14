import logging
from PIL import Image, ImageDraw
from modules import drawing_utils, asset_manager

def _get_caqi_data(airly_data):
    """Pomocnicza funkcja do wyciągania danych CAQI z odpowiedzi Airly."""
    if not airly_data or 'current' not in airly_data or 'indexes' not in airly_data['current']:
        return None

    for index in airly_data['current']['indexes']:
        if index.get('name') == 'AIRLY_CAQI':
            return {
                'value': round(index.get('value', 0)),
                'level': index.get('level', 'UNKNOWN').replace('_', ' ').title()
            }
    return None

def draw_panel(image, draw, weather_data, airly_data, fonts, panel_config):
    """Rysuje zintegrowany panel pogody i jakości powietrza."""
    rect = panel_config.get('rect', [0, 0, 0, 0])
    x1, y1, x2, y2 = rect
    panel_width = x2 - x1
    panel_height = y2 - y1
    
    adjustments = panel_config.get('positional_adjustments', {})
    x_offset = adjustments.get('x', 0)
    y_offset_config = adjustments.get('y', 0)

    # --- Dane ---
    current_icon_path = weather_data.get('icon')
    forecast_icon_path = weather_data.get('forecast_icon')
    weather_description = weather_data.get('weather_description', 'Brak opisu')
    current_temp_text = f"{weather_data.get('temp_real', '--')}°"
    humidity_text = f"{weather_data.get('humidity', '--')}%"
    pressure_text = f"{weather_data.get('pressure', '--')} hPa"
    caqi_data = _get_caqi_data(airly_data)
    caqi_text = str(caqi_data['value']) if caqi_data else "--"

    # --- Skalowanie ---
    scale_factor = 1.1

    # --- Czcionki ---
    font_temp = fonts.get('weather_temp_scaled')
    font_desc = fonts.get('tiny_scaled')
    font_small = fonts.get('calendar_day') # Reusing calendar font size 24

    # --- Rozmiary ---
    current_icon_size = int(60 * scale_factor)
    forecast_icon_size = int(current_icon_size * 0.4)
    small_icon_size = int(24 * 1.2 * scale_factor) # Original code had 1.2 here, keeping for now
    spacing_top = int(10 * scale_factor)
    spacing_bottom = int(20 * scale_factor)

    # --- Obliczanie wysokości contentu ---
    top_section_height = current_icon_size
    desc_section_height = font_desc.getbbox("A")[3]
    bottom_section_height = small_icon_size
    total_content_height = top_section_height + desc_section_height + bottom_section_height + int(30 * scale_factor) # 30 for spacing

    # --- Wyśrodkowanie pionowe ---
    y_offset_center = (panel_height - total_content_height) // 2
    y_offset = y_offset_center + y_offset_config
    
    # --- Rysowanie - sekcja górna (ikona, prognoza, temperatura) ---
    top_y_center = y1 + y_offset + top_section_height // 2
    
    temp_width = draw.textlength(current_temp_text, font=font_temp)
    total_top_width = current_icon_size + spacing_top + forecast_icon_size + spacing_top + temp_width
    current_x = x1 + (panel_width - total_top_width) // 2 + x_offset

    icon_img = drawing_utils.render_svg_with_cache(current_icon_path, size=current_icon_size) if current_icon_path else None
    if icon_img:
        icon_y = top_y_center - current_icon_size // 2
        image.paste(icon_img, (int(current_x), int(icon_y)), mask=icon_img)
    current_x += current_icon_size + spacing_top
    
    forecast_icon_img = drawing_utils.render_svg_with_cache(forecast_icon_path, size=forecast_icon_size) if forecast_icon_path else None
    if forecast_icon_img:
        icon_y = top_y_center - forecast_icon_size // 2 + int(15 * scale_factor)
        image.paste(forecast_icon_img, (int(current_x), int(icon_y)), mask=forecast_icon_img)
    current_x += forecast_icon_size + spacing_top

    draw.text((int(current_x), top_y_center), current_temp_text, font=font_temp, fill=drawing_utils.BLACK, anchor="lm")

    # --- Rysowanie - opis pogody ---
    description_y = y1 + y_offset + top_section_height + int(10 * scale_factor)
    description_text_width = draw.textlength(weather_description, font=font_desc)
    description_x = x1 + (panel_width - description_text_width) // 2 + x_offset
    draw.text((description_x, description_y), weather_description, font=font_desc, fill=drawing_utils.BLACK)

    # --- Rysowanie - sekcja dolna (wilgotność, ciśnienie, CAQI) ---
    bottom_y = y1 + y_offset + top_section_height + desc_section_height + int(30 * scale_factor)
    
    blocks = [
        {'icon_path': asset_manager.get_path('icon_humidity'), 'text': humidity_text},
        {'icon_path': asset_manager.get_path('icon_pressure'), 'text': pressure_text},
        {'icon_path': asset_manager.get_path('icon_air_quality'), 'text': caqi_text}
    ]
    
    total_text_width = sum(draw.textlength(b['text'], font=font_small) for b in blocks)
    total_icon_width = small_icon_size * len(blocks)
    total_width_of_blocks = total_text_width + total_icon_width + (spacing_bottom * (len(blocks)))
    
    current_x = x1 + (panel_width - total_width_of_blocks) // 2 + x_offset
    
    for block in blocks:
        icon = drawing_utils.render_svg_with_cache(block['icon_path'], size=small_icon_size)
        if icon:
            icon_y = bottom_y - icon.height // 2
            image.paste(icon, (int(current_x), int(icon_y)), mask=icon)
            current_x += icon.width + 5
        
        draw.text((int(current_x), bottom_y), block['text'], font=font_small, fill=drawing_utils.BLACK, anchor="lm")
        current_x += draw.textlength(block['text'], font=font_small) + spacing_bottom