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

    current_icon_path = weather_data.get('icon')
    forecast_icon_path = weather_data.get('forecast_icon')
    weather_description = weather_data.get('weather_description', 'Brak opisu')
    current_temp_text = f"{weather_data.get('temp_real', '--')}°"
    humidity_text = f"{weather_data.get('humidity', '--')}%"
    pressure_text = f"{weather_data.get('pressure', '--')} hPa"
    caqi_data = _get_caqi_data(airly_data)
    caqi_text = str(caqi_data['value']) if caqi_data else "--"

    scale_factor = 1.2 # New line

    top_y_center = y1 + int(30 * scale_factor) # Adjusted from 55
    current_icon_size = int(60 * scale_factor)  # Adjusted from 80
    forecast_icon_size = int(current_icon_size * 0.4)

    spacing_top = int(10 * scale_factor)
    temp_width = draw.textlength(current_temp_text, font=fonts['weather_temp'])
    total_top_width = current_icon_size + spacing_top + forecast_icon_size + spacing_top + temp_width
    
    current_x = x1 + (panel_width - total_top_width) // 2

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

    draw.text((int(current_x), top_y_center), current_temp_text, font=fonts['weather_temp'], fill=drawing_utils.DARK_GRAY, anchor="lm")

    # Draw weather description
    description_font = fonts['tiny']
    description_text_width = draw.textlength(weather_description, font=description_font)
    description_x = x1 + (panel_width - description_text_width) // 2
    description_y = y1 + int(65 * scale_factor)  # Position below the main icon/temp block

    draw.text((description_x, description_y), weather_description, font=description_font, fill=drawing_utils.DARK_GRAY)

    bottom_y = y1 + int(110 * scale_factor)  # Adjusted from 125
    small_font = fonts['small']
    small_icon_size = int(24 * 1.2 * scale_factor)
    
    blocks = [
        {'icon_path': asset_manager.get_path('icon_humidity'), 'text': humidity_text},
        {'icon_path': asset_manager.get_path('icon_pressure'), 'text': pressure_text},
        {'icon_path': asset_manager.get_path('icon_air_quality'), 'text': caqi_text}
    ]
    
    total_text_width = sum(draw.textlength(b['text'], font=small_font) for b in blocks)
    total_icon_width = small_icon_size * len(blocks)
    spacing_bottom = int(20 * scale_factor)
    total_width_of_blocks = total_text_width + total_icon_width + (spacing_bottom * (len(blocks)))
    
    current_x = x1 + (panel_width - total_width_of_blocks) // 2
    
    for block in blocks:
        icon = drawing_utils.render_svg_with_cache(block['icon_path'], size=small_icon_size)
        if icon:
            icon_y = bottom_y - icon.height // 2
            image.paste(icon, (int(current_x), int(icon_y)), mask=icon)
            current_x += icon.width + 5
        
        draw.text((int(current_x), bottom_y), block['text'], font=small_font, fill=drawing_utils.DARK_GRAY, anchor="lm")
        current_x += draw.textlength(block['text'], font=small_font) + spacing_bottom
    total_width_of_blocks = total_text_width + total_icon_width + (spacing_bottom * (len(blocks)))
    
    current_x = x1 + (panel_width - total_width_of_blocks) // 2
    
    for block in blocks:
        icon = drawing_utils.render_svg_with_cache(block['icon_path'], size=small_icon_size)
        if icon:
            icon_y = bottom_y - icon.height // 2
            image.paste(icon, (int(current_x), int(icon_y)), mask=icon)
            current_x += icon.width + 5
        
        draw.text((int(current_x), bottom_y), block['text'], font=small_font, fill=drawing_utils.DARK_GRAY, anchor="lm")
        current_x += draw.textlength(block['text'], font=small_font) + spacing_bottom