import os
import shutil
import logging

import config
from modules import path_manager

def sync_assets_to_cache():
    """
    Kopiuje cały katalog zasobów z katalogu projektu do pamięci podręcznej w RAM.
    Jest to kluczowe dla wydajności, aby uniknąć ciągłego odczytu z karty SD.
    """
    # Ścieżka źródłowa: assets w katalogu projektu
    source_assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
    # Ścieżka docelowa: assets w katalogu cache w RAM
    dest_assets_dir = path_manager.RUNTIME_ASSETS_DIR

    if not os.path.exists(source_assets_dir):
        logging.critical(f"Katalog źródłowy zasobów nie istnieje: {source_assets_dir}. Aplikacja nie może kontynuować.")
        raise FileNotFoundError(f"Missing source assets directory: {source_assets_dir}")

    try:
        logging.info(f"Synchronizowanie zasobów z '{source_assets_dir}' do '{dest_assets_dir}'...")
        # Usuń stary katalog zasobów w cache, jeśli istnieje, aby zapewnić świeżą kopię
        if os.path.exists(dest_assets_dir):
            shutil.rmtree(dest_assets_dir)

        # Skopiuj cały katalog
        shutil.copytree(source_assets_dir, dest_assets_dir)
        logging.info("Synchronizacja zasobów zakończona pomyślnie.")
    except Exception as e:
        logging.critical(f"Nie udało się zsynchronizować zasobów: {e}", exc_info=True)
        raise

def initialize_runtime_paths():
    """
    Dynamicznie buduje i ustawia pełne ścieżki do zasobów w module config.
    Ta funkcja musi być wywołana na starcie aplikacji, PO synchronizacji zasobów.
    Dzięki temu reszta aplikacji może używać `config.NAZWA_ZASOBU` bez martwienia się,
    gdzie te zasoby fizycznie się znajdują.
    """
    logging.info("Inicjalizowanie dynamicznych ścieżek zasobów w czasie rzeczywistym...")

    # Nadpisz ścieżki w module config, aby wskazywały na katalog w RAM
    config.FONT_ROBOTO_MONO_REGULAR = os.path.join(path_manager.RUNTIME_ASSETS_DIR, config.FONT_DIR, config.FONT_ROBOTO_MONO_REGULAR_FILENAME)
    config.FONT_ROBOTO_MONO_BOLD = os.path.join(path_manager.RUNTIME_ASSETS_DIR, config.FONT_DIR, config.FONT_ROBOTO_MONO_BOLD_FILENAME)
    config.FONT_EASTER_EGG = os.path.join(path_manager.RUNTIME_ASSETS_DIR, config.FONT_DIR, config.FONT_EASTER_EGG_FILENAME)

    config.ICON_FEATHER_PATH = os.path.join(path_manager.RUNTIME_ASSETS_DIR, config.ICON_FEATHER_SUBDIR)

    config.ICON_HUMIDITY_PATH = os.path.join(config.ICON_FEATHER_PATH, 'droplet.svg')
    config.ICON_PRESSURE_PATH = os.path.join(config.ICON_FEATHER_PATH, 'arrow-down.svg')
    config.ICON_SYNC_PROBLEM_PATH = os.path.join(config.ICON_FEATHER_PATH, 'alert-triangle.svg')
    config.ICON_AIR_QUALITY_PATH = os.path.join(config.ICON_FEATHER_PATH, 'bar-chart-2.svg')

    # Zbuduj ścieżki do obrazów, poprawnie wykorzystując config.IMG_DIR
    runtime_img_dir = os.path.join(path_manager.RUNTIME_ASSETS_DIR, config.IMG_DIR)
    config.SPLASH_WAVESHARE_LOGO_PATH = os.path.join(runtime_img_dir, config.SPLASH_WAVESHARE_LOGO_FILENAME)
    config.SPLASH_CIRCLE_LOGO_PATH = os.path.join(runtime_img_dir, config.SPLASH_CIRCLE_LOGO_FILENAME)
    config.EASTER_EGG_IMAGE_PATH = os.path.join(runtime_img_dir, config.EASTER_EGG_IMAGE_FILENAME)

    config.ICON_SUNRISE_PATH = os.path.join(config.ICON_FEATHER_PATH, 'sunrise.svg')
    config.ICON_SUNSET_PATH = os.path.join(config.ICON_FEATHER_PATH, 'sunset.svg')

    logging.info("Ścieżki zasobów wskazują teraz na katalog w pamięci podręcznej.")

def verify_assets():
    """
    Sprawdza, czy wszystkie krytyczne zasoby zdefiniowane w config istnieją fizycznie na dysku.
    Implementuje zasadę "fail-fast" - aplikacja zakończy działanie od razu, jeśli brakuje
    niezbędnego pliku, zamiast ulegać awarii później.
    """
    logging.info("Weryfikowanie istnienia krytycznych zasobów...")
    assets_to_check = [
        'FONT_ROBOTO_MONO_REGULAR',
        'FONT_ROBOTO_MONO_BOLD',
        'FONT_EASTER_EGG',
        'ICON_HUMIDITY_PATH',
        'ICON_PRESSURE_PATH',
        'ICON_SYNC_PROBLEM_PATH',
        'ICON_AIR_QUALITY_PATH',
        'ICON_SUNRISE_PATH',
        'ICON_SUNSET_PATH',
        'SPLASH_WAVESHARE_LOGO_PATH',
        'SPLASH_CIRCLE_LOGO_PATH',
        'EASTER_EGG_IMAGE_PATH'
    ]
    all_ok = True
    for asset_name in assets_to_check:
        path = getattr(config, asset_name, None)
        if not path or not os.path.exists(path):
            logging.critical(f"Krytyczny błąd: Brakujący plik zasobu '{asset_name}'. Oczekiwano go pod ścieżką: {path}")
            all_ok = False
    return all_ok
