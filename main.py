import logging
import threading
import argparse
import os
import shutil
import sys
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import config
from modules import time, weather, google_calendar, display, path_manager, startup_screens, drawing_utils, layout

# --- Niestandardowy Formater Logów ---
class CenteredFormatter(logging.Formatter):
    """Niestandardowy formater logów do centrowania zawartości w polach o stałej szerokości."""
    def __init__(self, fmt=None, datefmt=None, style='%', module_width=16, level_width=8):
        super().__init__(fmt, datefmt, style)
        self.module_width = module_width
        self.level_width = level_width

    def format(self, record):
        record.module_centered = record.module.center(self.module_width)
        record.levelname_centered = record.levelname.center(self.level_width)
        return super().format(record)

# Zmienna globalna przechowująca stan obrotu ekranu, dostępna dla zadań harmonogramu
should_flip = False


def update_all_data_sources(layout_config):
    """Uruchamia wszystkie moduły zbierające dane w odpowiedniej kolejności."""
    logging.info("Rozpoczynanie aktualizacji wszystkich źródeł danych...")
    time.update_time_data()
    weather.update_weather_data()
    google_calendar.update_calendar_data()
    logging.info("Zakończono aktualizację wszystkich źródeł danych.")

def deep_refresh_job(layout_config, draw_borders_flag=False):
    """Zadanie dla harmonogramu: wykonuje głębokie odświeżenie z przesunięciem pikseli o 3:00 w nocy."""
    try:
        logging.info("Rozpoczynanie zaplanowanego, głębokiego odświeżenia ekranu (3:00 w nocy).")
        update_all_data_sources(layout_config)

        logging.info("Wykonywanie pełnego, głębokiego odświeżenia z przesunięciem pikseli.")
        display.update_display(
            layout_config,
            force_full_refresh=True,
            draw_borders=draw_borders_flag,
            apply_pixel_shift=True,
            flip=should_flip
        )
    except Exception as e:
        logging.error(f"Błąd podczas głębokiego odświeżenia: {e}", exc_info=True)

def main_update_job(layout_config, draw_borders_flag=False):
    """Główne zadanie dla harmonogramu, uruchamiane co godzinę (z wyjątkiem 3:00)."""
    try:
        logging.info("Rozpoczynanie cogodzinnej, standardowej aktualizacji danych i ekranu...")
        update_all_data_sources(layout_config)

        logging.info("Wykonywanie standardowego odświeżenia ekranu.")
        display.update_display(
            layout_config,
            force_full_refresh=False,
            draw_borders=draw_borders_flag,
            apply_pixel_shift=False,
            flip=should_flip
        )
    except Exception as e:
        logging.error(f"Błąd podczas głównej aktualizacji: {e}", exc_info=True)

def time_update_job(layout_config, draw_borders_flag=False):
    """Zadanie dla harmonogramu: aktualizuje czas i wykonuje częściowe odświeżenie."""
    now = datetime.datetime.now()

    if now.hour == 21 and now.minute == 37:
        logging.info("Aktywacja Easter Egga...")
        try:
            startup_screens.display_easter_egg(display.EPD_LOCK, flip=should_flip)
        except Exception as e:
            logging.error(f"Błąd podczas wyświetlania Easter Egga: {e}", exc_info=True)
    else:
        logging.debug("Uruchamianie częściowej aktualizacji ekranu (tylko czas)...")
        try:
            # Aktualizujemy tylko plik z czasem, reszta zostaje bez zmian
            time.update_time_data()
            display.partial_update_time(layout_config, draw_borders=draw_borders_flag, flip=should_flip)
        except Exception as e:
            logging.error(f"Błąd podczas częściowej aktualizacji: {e}", exc_info=True)

def clear_cache_directory():
    """Czyści zawartość katalogu tymczasowego, zachowując sam katalog."""
    cache_dir = path_manager.CACHE_DIR
    logging.info(f"Czyszczenie zawartości katalogu tymczasowego: {cache_dir}")
    if os.path.exists(cache_dir):
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error(f"Błąd podczas usuwania {file_path}: {e}")
    else:
        os.makedirs(cache_dir, exist_ok=True)
    logging.info("Katalog tymczasowy wyczyszczony i gotowy do użycia.")

def copy_assets_to_tmp():
    """Kopiuje zasoby do katalogu tymczasowego w pamięci RAM."""
    source_dir = "assets"
    dest_dir = os.path.join(path_manager.CACHE_DIR, source_dir)
    logging.info(f"Kopiowanie zasobów z '{source_dir}' do '{dest_dir}'...")
    if not os.path.isdir(source_dir):
        logging.critical(f"Katalog źródłowy '{source_dir}' nie istnieje. Aplikacja nie może kontynuować.")
        sys.exit(1)
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)

def remap_config_paths_to_cache():
    """Aktualizuje ścieżki w 'config', aby wskazywały na zasoby w cache'u."""
    logging.info("Mapowanie ścieżek zasobów na katalog tymczasowy...")
    for attr_name in dir(config):
        if not attr_name.isupper() or not isinstance(getattr(config, attr_name), str):
            continue
        if attr_name.endswith(('_PATH', '_FILE', '_DIR')):
            original_path = getattr(config, attr_name)
            if original_path.startswith('assets/'):
                new_path = os.path.join(path_manager.CACHE_DIR, original_path)
                setattr(config, attr_name, new_path)
                logging.debug(f"Zmapowano '{attr_name}': '{original_path}' -> '{new_path}'")

def main():
    """Główna funkcja aplikacji."""
    parser = argparse.ArgumentParser(description="Waveshare E-Paper Dashboard")
    parser.add_argument('--draw-borders', action='store_true', help='Rysuje granice wokół paneli.')
    parser.add_argument('--service', action='store_true', help='Optymalizuje logowanie dla systemd.')
    parser.add_argument('--2137', dest='show_easter_egg_on_start', action='store_true', help='Wyświetla Easter Egg przy starcie.')
    parser.add_argument('--no-splash', action='store_true', help='Pomija ekran powitalny.')
    parser.add_argument('--verbose', action='store_true', help='Włącza logowanie DEBUG.')
    parser.add_argument('--flip', action='store_true', help='Obraca obraz o 180 stopni, nadpisując ustawienie z config.py.')
    args = parser.parse_args()

    log_format = '[%(module_centered)s][%(levelname_centered)s] %(message)s' if args.service else '%(asctime)s [%(module_centered)s][%(levelname_centered)s] %(message)s'
    formatter = CenteredFormatter(fmt=log_format, datefmt='%Y-%m-%d %H:%M:%S', module_width=15, level_width=8)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    if not args.verbose:
        # Ukryj zbyt gadatliwe logi z biblioteki Google, chyba że jest włączony tryb --verbose
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

    if args.service and not args.verbose:
        logging.info("Tryb --service aktywny, ograniczanie gadatliwych logów.")
        # Wyciszanie logów z apscheduler, które informują o każdym uruchomieniu zadania
        logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
        logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)

    logging.info("--- Inicjalizacja Dashboardu Waveshare ---")

    layout_config = layout.load_layout()
    if not layout_config:
        logging.critical("Nie udało się wczytać konfiguracji layoutu. Aplikacja nie może kontynuować.")
        sys.exit(1)


    clear_cache_directory()
    copy_assets_to_tmp()
    remap_config_paths_to_cache()

    # Ustawienie globalnej zmiennej na podstawie konfiguracji i flagi
    global should_flip
    should_flip = getattr(config, 'FLIP_DISPLAY', False) or args.flip

    splash_thread = None
    if args.show_easter_egg_on_start:
        splash_thread = threading.Thread(target=startup_screens.display_easter_egg, args=(display.EPD_LOCK, should_flip), name="EasterEggThread")
        splash_thread.start()
    elif not args.no_splash:
        splash_thread = threading.Thread(target=startup_screens.display_splash_screen, args=(display.EPD_LOCK, should_flip), name="SplashThread")
        splash_thread.start()

    update_all_data_sources(layout_config)

    if splash_thread:
        logging.info("Oczekiwanie na zakończenie ekranu powitalnego...")
        splash_thread.join()

    logging.info("Wykonywanie pierwszego, pełnego renderowania ekranu...")
    display.update_display(
        layout_config,
        force_full_refresh=True,
        draw_borders=args.draw_borders,
        apply_pixel_shift=True,
        flip=should_flip)
    logging.info("Pierwsze renderowanie zakończone.")

    scheduler = BlockingScheduler(timezone="Europe/Warsaw")
    scheduler.add_job(time_update_job, 'cron', minute='*', second=1, id='time_update_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders})
    scheduler.add_job(main_update_job, 'cron', hour='0-2,4-23', minute=0, second=5, id='main_update_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders})
    scheduler.add_job(deep_refresh_job, 'cron', hour=3, minute=0, second=5, id='deep_refresh_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders})

    logging.info("--- Harmonogram uruchomiony. Aplikacja działa poprawnie. ---")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Otrzymano sygnał zamknięcia. Czyszczenie ekranu...")
        display.clear_display()
        logging.info("Aplikacja zamknięta.")

if __name__ == "__main__":
    main()
