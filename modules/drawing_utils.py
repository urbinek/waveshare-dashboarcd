import logging
import os
import io
import textwrap
from functools import lru_cache
from PIL import Image, ImageFont

# Użyj cairosvg jeśli jest dostępne, jest znacznie szybsze i lepsze niż svglib
try:
    from cairosvg import svg2png
    SVG_RENDERER = 'cairosvg'
except ImportError:
    # svglib jest wolniejszy i ma problemy z niektórymi plikami SVG
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    SVG_RENDERER = 'svglib'
    logging.warning("Biblioteka 'cairosvg' nie jest zainstalowana (`pip install cairosvg`). Używam wolniejszej biblioteki 'svglib'. Zalecana jest instalacja cairosvg dla lepszej wydajności.")

import config

@lru_cache(maxsize=None)
def load_fonts():
    """
    Wczytuje wszystkie zdefiniowane w konfiguracji czcionki.
    Dzięki dekoratorowi @lru_cache, czcionki są wczytywane z dysku tylko raz,
    co znacząco przyspiesza operacje rysowania.
    """
    logging.info("Wczytywanie czcionek do pamięci podręcznej (pierwsze uruchomienie)...")
    fonts = {}
    try:
        fonts['large'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 96)
        fonts['medium'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 32)
        fonts['small'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_REGULAR, 20)
        fonts['small_bold'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 20)
        fonts['weather_temp'] = ImageFont.truetype(config.FONT_ROBOTO_MONO_BOLD, 72)
        logging.info("Wszystkie czcionki wczytane pomyślnie.")
    except IOError as e:
        logging.critical(f"Nie udało się wczytać pliku czcionki: {e}. Upewnij się, że ścieżki w config.py są poprawne.")
        # W przypadku błędu, zwróć domyślne czcionki, aby aplikacja mogła próbować działać dalej
        fonts['large'] = ImageFont.load_default()
        fonts['medium'] = ImageFont.load_default()
        fonts['small'] = ImageFont.load_default()
        fonts['small_bold'] = ImageFont.load_default()
        fonts['weather_temp'] = ImageFont.load_default()
    return fonts

@lru_cache(maxsize=128)
def render_svg_with_cache(svg_path, size):
    """
    Renderuje plik SVG do obiektu obrazu Pillow, z agresywnym cachingiem.
    Loguje informację o renderowaniu tylko przy pierwszym wczytaniu danego zasobu (cache miss).
    Kluczem cache'a jest kombinacja ścieżki pliku i rozmiaru.
    Zwraca obiekt obrazu Pillow w trybie RGBA.
    """
    if not svg_path:
        logging.warning("Wywołano render_svg_with_cache z pustą ścieżką (svg_path=None).")
        return None

    if not os.path.exists(svg_path):
        logging.error(f"Plik SVG nie istnieje pod ścieżką: {svg_path}")
        return None

    # Ten log pojawi się tylko wtedy, gdy zasób nie jest w cache (cache miss).
    # Zmieniamy na DEBUG, aby nie zaśmiecać logów. Specjalne logowanie będzie w panelu.
    logging.debug(f"Renderowanie SVG (cache miss): {svg_path}")

    try:
        if SVG_RENDERER == 'cairosvg':
            png_data = svg2png(url=svg_path, output_width=size, output_height=size)
            in_memory_file = io.BytesIO(png_data)
            image = Image.open(in_memory_file).convert("RGBA")
        else: # svglib
            drawing = svg2rlg(svg_path)
            in_memory_file = io.BytesIO()
            renderPM.drawToFile(drawing, in_memory_file, fmt="PNG", bg=0xFFFFFF, configPIL={'transparent': 1})
            in_memory_file.seek(0)
            image = Image.open(in_memory_file).resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
        return image
    except Exception as e:
        logging.error(f"Nie udało się zrenderować SVG '{svg_path}' za pomocą {SVG_RENDERER}: {e}")
        return None

def draw_error_message(draw_obj, message, fonts, panel_config):
    """Rysuje komunikat o błędzie w zadanym obszarze."""
    rect = panel_config.get('rect', [0, 0, 800, 480])
    x1, y1, x2, y2 = rect
    font = fonts.get('small', ImageFont.load_default())
    char_width_approx = font.getlength('W')
    max_chars = (x2 - x1 - 20) / char_width_approx if char_width_approx > 0 else 30
    wrapped_text = textwrap.fill(message, width=int(max_chars))
    draw_obj.text((x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2), wrapped_text, font=font, fill=0, anchor="mm", align="center")
