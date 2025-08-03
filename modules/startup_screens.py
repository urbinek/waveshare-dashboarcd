import logging
import os
from PIL import Image, ImageDraw, ImageChops

from modules import drawing_utils, asset_manager

try:
    from waveshare_epd import epd7in5b_V2
    EPD_WIDTH = epd7in5b_V2.EPD_WIDTH
    EPD_HEIGHT = epd7in5b_V2.EPD_HEIGHT
except (ImportError, RuntimeError):
    EPD_WIDTH = 800
    EPD_HEIGHT = 480

def display_splash_screen(epd_lock, flip=False):
    """Wyświetla ekran powitalny (splash screen) podczas inicjalizacji."""
    try:
        waveshare_logo_path = asset_manager.get_path('splash_logo_waveshare')
        circle_logo_path = asset_manager.get_path('splash_logo_circle')
    except KeyError as e:
        logging.error(f"Brak zdefiniowanego zasobu dla ekranu powitalnego: {e}! Pomijanie...")
        return

    try:
        logging.debug("Oczekiwanie na blokadę EPD dla ekranu powitalnego...")
        with epd_lock:
            logging.info("Wyświetlanie ekranu powitalnego...")
            epd = epd7in5b_V2.EPD()
            epd.init()
            epd.Clear()

        fonts = drawing_utils.load_fonts()
        dashboard_font = fonts.get('medium')

        black_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)
        red_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)
        draw_black = ImageDraw.Draw(black_image)

        left_box_rect = (0, 0, EPD_WIDTH // 2, EPD_HEIGHT)
        right_box_rect = (EPD_WIDTH // 2, 0, EPD_WIDTH, EPD_HEIGHT)

        waveshare_logo = drawing_utils.render_svg_with_cache(waveshare_logo_path, size=360)
        if waveshare_logo:
            img_x = (left_box_rect[2] - waveshare_logo.width) // 2
            img_y = (left_box_rect[3] - waveshare_logo.height) // 2
            mask = waveshare_logo.getchannel('A').point(lambda i: i > 128, '1')
            black_image.paste(0, (img_x, img_y), mask)

        circle_logo = drawing_utils.render_svg_with_cache(circle_logo_path, size=150)
        dashboard_text = "DASHBOARD"
        text_padding = 15

        text_bbox = draw_black.textbbox((0, 0), dashboard_text, font=dashboard_font)
        text_height = text_bbox[3] - text_bbox[1]
        circle_logo_height = circle_logo.height if circle_logo else 0
        total_height = circle_logo_height + text_padding + text_height

        block_y_start = (right_box_rect[3] - total_height) // 2
        if circle_logo:
            circle_x = right_box_rect[0] + ((right_box_rect[2] - right_box_rect[0]) - circle_logo.width) // 2
            mask = circle_logo.getchannel('A').point(lambda i: i > 128, '1')
            black_image.paste(0, (circle_x, block_y_start), mask)

        text_x = right_box_rect[0] + (right_box_rect[2] - right_box_rect[0]) // 2
        text_y = block_y_start + circle_logo_height + text_padding
        draw_black.text((text_x, text_y), dashboard_text, font=dashboard_font, fill=0, anchor="mt")

        black_image = ImageChops.invert(black_image)

        if flip:
            logging.info("Obracanie ekranu powitalnego o 180 stopni.")
            black_image = black_image.rotate(180)
            red_image = red_image.rotate(180)

        epd.display(epd.getbuffer(black_image), epd.getbuffer(red_image))
        logging.info("Wyświetlanie ekranu powitalnego zakończone.")

    except Exception as e:
        logging.error(f"Wystąpił błąd podczas wyświetlania ekranu powitalnego: {e}", exc_info=True)

def display_easter_egg(epd_lock, flip=False):
    """Wyświetla specjalny obraz 'easter egg'."""
    try:
        easter_egg_image_path = asset_manager.get_path('easter_egg_image')
    except KeyError as e:
        logging.error(f"Brak zdefiniowanego zasobu dla Easter Egga: {e}! Pomijanie...")
        return

    try:
        logging.debug("Oczekiwanie na blokadę EPD dla Easter Egga...")
        with epd_lock:
            logging.info("Wyświetlanie Easter Egga...")
            epd = epd7in5b_V2.EPD()
            epd.init()
            epd.Clear()

        fonts = drawing_utils.load_fonts()
        easter_egg_font = fonts.get('easter_egg', fonts['large'])

        black_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)
        red_image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)
        draw_black = ImageDraw.Draw(black_image)

        source_img = Image.open(easter_egg_image_path)

        side_box_width = 200
        middle_box_width = EPD_WIDTH - (2 * side_box_width)

        ratio_w = middle_box_width / source_img.width
        ratio_h = EPD_HEIGHT / source_img.height
        ratio = min(ratio_w, ratio_h)

        new_width = int(source_img.width * ratio)
        new_height = int(source_img.height * ratio)
        easter_egg_img = source_img.resize((new_width, new_height), Image.Resampling.LANCZOS).convert('1')

        box_center_y = EPD_HEIGHT // 2

        left_box_center_x = side_box_width // 2
        draw_black.text((left_box_center_x, box_center_y), "21", font=easter_egg_font, fill=0, anchor="mm")

        img_x = side_box_width + (middle_box_width - new_width) // 2
        img_y = (EPD_HEIGHT - new_height) // 2
        black_image.paste(easter_egg_img, (img_x, img_y))

        right_box_center_x = side_box_width + middle_box_width + (side_box_width // 2)
        draw_black.text((right_box_center_x, box_center_y), "37", font=easter_egg_font, fill=0, anchor="mm")

        if flip:
            logging.info("Obracanie ekranu Easter Egg o 180 stopni.")
            black_image = black_image.rotate(180)
            red_image = red_image.rotate(180)

        epd.display(epd.getbuffer(black_image), epd.getbuffer(red_image))
        logging.info("Wyświetlanie Easter Egga zakończone.")
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas wyświetlania Easter Egga: {e}", exc_info=True)
