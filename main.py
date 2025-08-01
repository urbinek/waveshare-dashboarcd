import logging
import threading
import argparse
import os
import shutil
import sys
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from modules import time, weather, google_calendar, display, path_manager, startup_screens, drawing_utils, layout, asset_manager, airly
import config

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
    airly.update_airly_data() # Pobierz dane Airly PRZED danymi pogodowymi
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

    try:
        # 1. Utwórz katalog cache, jeśli nie istnieje
        os.makedirs(path_manager.CACHE_DIR, exist_ok=True)

        # 2. Skopiuj wszystkie zasoby do katalogu cache w RAM
        asset_manager.sync_assets_to_cache()

        # 3. Zbuduj i ustaw dynamiczne ścieżki w module config
        asset_manager.initialize_runtime_paths()

        # 4. Sprawdź, czy wszystkie krytyczne zasoby faktycznie istnieją
        if not asset_manager.verify_assets():
            logging.critical("Weryfikacja zasobów nie powiodła się. Sprawdź powyższe logi, aby zobaczyć, których plików brakuje.")
            sys.exit(1)

    except Exception as e:
        logging.critical(f"Błąd krytyczny podczas inicjalizacji zasobów: {e}. Zamykanie.", exc_info=True)
        sys.exit(1)

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
