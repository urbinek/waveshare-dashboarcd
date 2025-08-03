import os
import shutil
import logging

from modules.config_loader import config
from modules import path_manager

# Słownik do przechowywania dynamicznie tworzonych ścieżek do zasobów
_asset_paths = {}

def sync_assets_to_cache():
    """
    Kopiuje zasoby z katalogu projektu do pamięci podręcznej w RAM.
    """
    source_assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
    dest_assets_dir = path_manager.RUNTIME_ASSETS_DIR

    if not os.path.exists(source_assets_dir):
        logging.critical(f"Katalog źródłowy zasobów nie istnieje: {source_assets_dir}.")
        raise FileNotFoundError(f"Missing source assets directory: {source_assets_dir}")

    try:
        logging.info(f"Synchronizowanie zasobów z '{source_assets_dir}' do '{dest_assets_dir}'...")
        if os.path.exists(dest_assets_dir):
            shutil.rmtree(dest_assets_dir)
        shutil.copytree(source_assets_dir, dest_assets_dir)
        logging.info("Synchronizacja zasobów zakończona pomyślnie.")
    except Exception as e:
        logging.critical(f"Nie udało się zsynchronizować zasobów: {e}", exc_info=True)
        raise

def initialize_runtime_paths():
    """
    Inicjalizuje ścieżki do zasobów, które znajdują się w pamięci podręcznej.
    """
    logging.info("Inicjalizowanie dynamicznych ścieżek zasobów w czasie rzeczywistym...")
    assets_config = config['assets']
    runtime_font_dir = os.path.join(path_manager.RUNTIME_ASSETS_DIR, os.path.basename(assets_config['fonts_dir']))
    runtime_icon_dir = os.path.join(path_manager.RUNTIME_ASSETS_DIR, os.path.basename(assets_config['icons_dir']))
    runtime_img_dir = os.path.join(path_manager.RUNTIME_ASSETS_DIR, os.path.basename(assets_config['images_dir']))
    feather_icons_path = os.path.join(runtime_icon_dir, assets_config['icons_feather_subdir'])

    # Definicje ścieżek do zasobów
    _asset_paths.update({
        'font_regular': os.path.join(runtime_font_dir, assets_config['font_regular']),
        'font_bold': os.path.join(runtime_font_dir, assets_config['font_bold']),
        'font_easter_egg': os.path.join(runtime_font_dir, assets_config['font_easter_egg']),
        'icons_feather_path': feather_icons_path,
        'icon_humidity': os.path.join(feather_icons_path, 'droplet.svg'),
        'icon_pressure': os.path.join(feather_icons_path, 'arrow-down.svg'),
        'icon_sync_problem': os.path.join(feather_icons_path, 'alert-triangle.svg'),
        'icon_air_quality': os.path.join(feather_icons_path, 'bar-chart-2.svg'),
        'icon_sunrise': os.path.join(feather_icons_path, 'sunrise.svg'),
        'icon_sunset': os.path.join(feather_icons_path, 'sunset.svg'),
        'splash_logo_waveshare': os.path.join(runtime_img_dir, assets_config['splash_logo_waveshare']),
        'splash_logo_circle': os.path.join(runtime_img_dir, assets_config['splash_logo_circle']),
        'easter_egg_image': os.path.join(runtime_img_dir, assets_config['easter_egg_image'])
    })
    logging.info("Ścieżki zasobów wskazują teraz na katalog w pamięci podręcznej.")

def get_path(asset_name: str) -> str:
    """
    Zwraca pełną, dynamiczną ścieżkę do zasobu na podstawie jego klucza.
    """
    path = _asset_paths.get(asset_name)
    if not path:
        raise KeyError(f"Zasób o nazwie '{asset_name}' nie został znaleziony. Sprawdź, czy jest zdefiniowany w initialize_runtime_paths.")
    return path

def verify_assets():
    """
    Sprawdza, czy wszystkie zdefiniowane zasoby istnieją fizycznie na dysku.
    """
    logging.info("Weryfikowanie istnienia krytycznych zasobów...")
    all_ok = True
    for asset_name, path in _asset_paths.items():
        if not os.path.exists(path):
            logging.critical(f"Krytyczny błąd: Brakujący plik zasobu '{asset_name}'. Oczekiwano go pod ścieżką: {path}")
            all_ok = False
    return all_ok
