import logging
import threading
import argparse
import os
import sys
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from modules import time, weather, google_calendar, display, path_manager, startup_screens, asset_manager, airly, accuweather
from modules.config_loader import config

class CenteredFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', module_width=16, level_width=8):
        super().__init__(fmt, datefmt, style)
        self.module_width = module_width
        self.level_width = level_width

    def format(self, record):
        record.module_centered = record.module.center(self.module_width)
        record.levelname_centered = record.levelname.center(self.level_width)
        return super().format(record)

should_flip = False

def update_all_data_sources(verbose_mode=False):
    logging.info("Rozpoczynanie aktualizacji wszystkich źródeł danych...")
    airly_thread = threading.Thread(target=airly.update_airly_data, args=(verbose_mode,))
    accuweather_thread = threading.Thread(target=accuweather.update_accuweather_data, args=(verbose_mode,))
    google_calendar_thread = threading.Thread(target=google_calendar.update_calendar_data, args=(verbose_mode,))

    airly_thread.start()
    accuweather_thread.start()
    google_calendar_thread.start()

    airly_thread.join()
    accuweather_thread.join()

    time.update_time_data()
    weather.update_weather_data()
    google_calendar_thread.join()
    logging.info("Zakończono aktualizację wszystkich źródeł danych.")

def deep_refresh_job(layout_config, draw_borders_flag=False, verbose_mode=False):
    try:
        logging.info("Rozpoczynanie zaplanowanego, głębokiego odświeżenia ekranu.")
        update_all_data_sources(verbose_mode)
        display.update_display(
            layout_config,
            force_full_refresh=True,
            draw_borders=draw_borders_flag,
            apply_pixel_shift=True,
            flip=should_flip
        )
    except Exception as e:
        logging.error(f"Błąd podczas głębokiego odświeżenia: {e}", exc_info=True)

def main_update_job(layout_config, draw_borders_flag=False, verbose_mode=False):
    try:
        logging.info("Rozpoczynanie cogodzinnej, standardowej aktualizacji.")
        update_all_data_sources(verbose_mode)
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
            time.update_time_data()
            display.partial_update_time(layout_config, draw_borders=draw_borders_flag, flip=should_flip)
        except Exception as e:
            logging.error(f"Błąd podczas częściowej aktualizacji: {e}", exc_info=True)

def main():
    parser = argparse.ArgumentParser(description="Waveshare E-Paper Dashboard")
    parser.add_argument('--draw-borders', action='store_true', help='Rysuje granice wokół paneli.')
    parser.add_argument('--service', action='store_true', help='Optymalizuje logowanie dla systemd.')
    parser.add_argument('--2137', dest='show_easter_egg_on_start', action='store_true', help='Wyświetla Easter Egg przy starcie.')
    parser.add_argument('--no-splash', action='store_true', help='Pomija ekran powitalny.')
    parser.add_argument('--verbose', action='store_true', help='Włącza logowanie DEBUG.')
    parser.add_argument('--flip', action='store_true', help='Obraca obraz o 180 stopni.')
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
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    if args.service and not args.verbose:
        logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
        logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)

    logging.info("--- Inicjalizacja Dashboardu Waveshare ---")

    layout_config = config.get('panels', {})
    if not layout_config:
        logging.critical("Brak konfiguracji layoutu w pliku config.yaml. Aplikacja nie może kontynuować.")
        sys.exit(1)

    try:
        os.makedirs(path_manager.CACHE_DIR, exist_ok=True)
        asset_manager.sync_assets_to_cache()
        asset_manager.initialize_runtime_paths()
        if not asset_manager.verify_assets():
            logging.critical("Weryfikacja zasobów nie powiodła się. Sprawdź logi.")
            sys.exit(1)
    except Exception as e:
        logging.critical(f"Błąd krytyczny podczas inicjalizacji zasobów: {e}.", exc_info=True)
        sys.exit(1)

    global should_flip
    should_flip = config['app'].get('flip_display', False) or args.flip

    splash_thread = None
    if args.show_easter_egg_on_start:
        splash_thread = threading.Thread(target=startup_screens.display_easter_egg, args=(display.EPD_LOCK, should_flip), name="EasterEggThread")
    elif not args.no_splash:
        splash_thread = threading.Thread(target=startup_screens.display_splash_screen, args=(display.EPD_LOCK, should_flip), name="SplashThread")
    
    if splash_thread:
        splash_thread.start()

    update_all_data_sources(args.verbose)

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
    scheduler.add_job(main_update_job, 'cron', hour='0-2,4-23', minute=0, second=5, id='main_update_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders, 'verbose_mode': args.verbose})
    scheduler.add_job(deep_refresh_job, 'cron', hour=3, minute=0, second=5, id='deep_refresh_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders, 'verbose_mode': args.verbose})

    logging.info("--- Harmonogram uruchomiony. Aplikacja działa poprawnie. ---")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Otrzymano sygnał zamknięcia. Czyszczenie ekranu...")
        display.clear_display()
        logging.info("Aplikacja zamknięta.")

if __name__ == "__main__":
    main()