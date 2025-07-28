import logging
import os
import io
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageChops

import config
from modules import path_manager

try:
    import cairosvg
    CAIRO_SVG_AVAILABLE = True
except Exception as e:
    CAIRO_SVG_AVAILABLE = False
    logging.warning(f"Biblioteka 'cairosvg' nie jest dostępna (błąd: {e}). Ikony nie będą wyświetlane. Upewnij się, że jest zainstalowana (`pip install cairosvg`) oraz że jej zależności systemowe są obecne.")

ICON_CACHE_DIR = os.path.join(path_manager.CACHE_DIR, 'icon_cache')

# Globalna zmienna do przechowywania wczytanych czcionek, aby uniknąć wielokrotnego wczytywania z dysku.
_loaded_fonts = None

def load_fonts():
    """
    Wczytuje czcionki przy pierwszym wywołaniu i zwraca je w słowniku.
    Przy kolejnych wywołaniach zwraca czcionki z pamięci podręcznej.
    """
    global _loaded_fonts
    if _loaded_fonts:
        return _loaded_fonts

    fonts = {}
    try:
        fonts['large'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 135)
        fonts['weather_temp'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_REGULAR, 65)
        fonts['medium'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 32)
        fonts['small'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_REGULAR, 20)
        fonts['small_bold'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 20)
        fonts['easter_egg'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 160)
    except IOError as e:
        logging.error(f"Błąd (IOError) podczas wczytywania czcionek: {e}. Używam czcionek domyślnych.")
        for key in ['large', 'weather_temp', 'medium', 'small', 'small_bold', 'easter_egg']:
            if key not in fonts:
                fonts[key] = ImageFont.load_default()

    _loaded_fonts = fonts
    return _loaded_fonts

def render_svg_with_cache(svg_path, width=None, height=None, size=None):
    """
    Renderuje plik SVG do obrazu PIL.Image, używając cache'u na dysku.
    Automatycznie wybiera metodę renderowania na podstawie ścieżki pliku:
    - Dithering dla ikon pogody (jeśli ścieżka zawiera 'imgw').
    - Wysoki kontrast (kanał alfa) dla pozostałych ikon (np. logo).
    """
    if not CAIRO_SVG_AVAILABLE:
        logging.warning("Próba renderowania SVG, ale 'cairosvg' jest niedostępne.")
        return Image.new('1', (width or size or 1, height or size or 1), 255)

    if size:
        width = width or size
        height = height or size

    # Wybierz metodę renderowania na podstawie ścieżki pliku
    # Ikony pogody zawierają 'imgw' w ścieżce i wymagają ditheringu
    render_method = 'dither' if 'imgw' in svg_path else 'alpha'

    os.makedirs(ICON_CACHE_DIR, exist_ok=True)

    normalized_path = os.path.normpath(svg_path)
    path_parts = normalized_path.split(os.sep)
    cache_filename_base = "_".join(path_parts[-3:])
    size_str = f"{width or 'auto'}x{height or 'auto'}"
    # Dodaj metodę renderowania do nazwy pliku w cache, aby uniknąć konfliktów
    cache_filename = f"{os.path.splitext(cache_filename_base)[0]}_{size_str}_{render_method}.png"
    cache_path = os.path.join(ICON_CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        logging.debug(f"Użyto ikony z cache: {cache_path}")
        return Image.open(cache_path)

    logging.debug(f"Renderowanie ikony: {svg_path} (metoda: {render_method})")
    png_data = cairosvg.svg2png(url=svg_path, output_width=width, output_height=height)
    rgba_image = Image.open(io.BytesIO(png_data))

    if render_method == 'dither':
        # Metoda z ditheringiem, lepsza dla złożonych ikon (pogoda).
        # Należy najpierw nałożyć obraz z przezroczystością na białe tło,
        # aby uniknąć czarnego kwadratu w miejscu przezroczystości.
        background = Image.new("RGBA", rgba_image.size, (255, 255, 255, 255))
        # Nałóż obraz z przezroczystością na białe tło
        composited_image = Image.alpha_composite(background, rgba_image)
        # Dopiero teraz konwertujemy do skali szarości i 1-bit z ditheringiem.
        final_image = composited_image.convert('L').convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    else: # render_method == 'alpha'
        # Metoda wysokiego kontrastu, dobra dla prostych logo
        # Użyj kanału alfa do stworzenia ostrego, czarno-białego obrazu
        alpha = rgba_image.split()[3]
        inverted_alpha = ImageChops.invert(alpha)
        final_image = inverted_alpha.convert('1', dither=Image.Dither.NONE)

    final_image.save(cache_path)
    return final_image

def draw_error_message(draw_obj, message, fonts, box_info):
    """Rysuje wycentrowaną wiadomość o błędzie w danym boksie."""
    rect = box_info['rect']
    box_width = rect[2] - rect[0]
    box_height = rect[3] - rect[1]
    x_center = rect[0] + box_width // 2
    y_center = rect[1] + box_height // 2
    font = fonts.get('small_bold', ImageFont.load_default())
    wrapped_text = textwrap.fill(message, width=35)
    draw_obj.text((x_center, y_center), wrapped_text, font=font, fill=0, anchor="mm", align="center")
