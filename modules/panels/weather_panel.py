import logging
from PIL import Image
from modules import drawing_utils
import config

def _draw_text_only_layout(draw, weather_data, fonts, box_info):
    """Rysuje uproszczony, tekstowy layout pogody w przypadku braku ikon."""
    logging.warning("Użyto zastępczego layoutu dla pogody (tylko tekst).")
    rect = box_info['rect']
    x_center = rect[0] + (rect[2] - rect[0]) // 2

    temp_text = f"{weather_data.get('temp_real', '--')}°C"
    draw.text((x_center, rect[1] + 60), temp_text, font=fonts['weather_temp'], fill=0, anchor="mt")

    details_y = rect[1] + 120
    details_text = (
        f"Wilgotność: {weather_data.get('humidity', '--')}%\n"
        f"Ciśnienie: {weather_data.get('pressure', '--')} hPa"
    )
    draw.multiline_text((x_center, details_y), details_text, font=fonts['small'], fill=0, anchor="ma", align="center", spacing=6)

def draw_panel(image, draw, weather_data, fonts, box_info):
    """
    Rysuje uproszczony panel pogody z ikoną, temperaturą, wilgotnością i ciśnieniem.
    Layout:
    {ikona pogody} {temperatura}
    {ikona wilg.}{wilgotność} {ikona ciś.}{ciśnienie}
    """
    try:
        rect = box_info['rect']
        x0, y0, x1, y1 = rect
        panel_width = x1 - x0
        panel_height = y1 - y0
        padding = 20

        # --- Górny wiersz: Ikona pogody i temperatura ---
        main_icon_path = weather_data.get('icon', config.DEFAULT_WEATHER_ICON_PATH)
        main_icon_size = 90
        main_icon_image = drawing_utils.render_svg_with_cache(main_icon_path, size=main_icon_size)

        if not main_icon_image:
             raise ValueError(f"Nie można wyrenderować głównej ikony pogody: {main_icon_path}")

        temp_text = f"{weather_data.get('temp_real', '--')}°C"
        temp_font = fonts['weather_temp']

        temp_text_width = int(draw.textlength(temp_text, font=temp_font))
        total_top_width = main_icon_size + padding + temp_text_width
        start_x_top = x0 + (panel_width - total_top_width) // 2

        icon_x = start_x_top
        icon_y = y0 + 15
        image.paste(main_icon_image, (int(icon_x), int(icon_y)), main_icon_image if main_icon_image.mode == 'RGBA' else None)

        temp_x = icon_x + main_icon_size + padding
        temp_y = icon_y + main_icon_size // 2
        draw.text((int(temp_x), int(temp_y)), temp_text, font=temp_font, fill=0, anchor="lm")

        # --- Dolny wiersz: Wilgotność i ciśnienie ---
        details_font = fonts['small']
        details_icon_size = 24

        # Zmieniono pozycjonowanie: środek dolnego wiersza jest teraz 50px poniżej środka temperatury,
        # co zmniejsza odstęp. Poprzednio był on zakotwiczony do dołu panelu.
        details_y_center = temp_y + 50
        details_y = details_y_center - (details_icon_size // 2)

        humidity_icon = drawing_utils.render_svg_with_cache(config.ICON_HUMIDITY_PATH, size=details_icon_size)
        pressure_icon = drawing_utils.render_svg_with_cache(config.ICON_PRESSURE_PATH, size=details_icon_size)

        humidity_text = f"{weather_data.get('humidity', '--')}%"
        pressure_text = f"{weather_data.get('pressure', '----')} hPa"
        humidity_block_width = details_icon_size + 5 + int(draw.textlength(humidity_text, font=details_font))
        pressure_block_width = details_icon_size + 5 + int(draw.textlength(pressure_text, font=details_font))
        total_bottom_width = humidity_block_width + padding + pressure_block_width
        start_x_bottom = x0 + (panel_width - total_bottom_width) // 2

        humidity_icon_x = start_x_bottom
        image.paste(humidity_icon, (int(humidity_icon_x), int(details_y)), humidity_icon if humidity_icon.mode == 'RGBA' else None)
        draw.text((int(humidity_icon_x + details_icon_size + 5), int(details_y_center)), humidity_text, font=details_font, fill=0, anchor='lm')

        pressure_icon_x = humidity_icon_x + humidity_block_width + padding
        image.paste(pressure_icon, (int(pressure_icon_x), int(details_y)), pressure_icon if pressure_icon.mode == 'RGBA' else None)
        draw.text((int(pressure_icon_x + details_icon_size + 5), int(details_y_center)), pressure_text, font=details_font, fill=0, anchor='lm')

    except Exception as e:
        logging.error(f"Błąd podczas renderowania panelu pogody: {e}", exc_info=True)
        _draw_text_only_layout(draw, weather_data, fonts, box_info)
