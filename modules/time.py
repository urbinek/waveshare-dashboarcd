import os
import json
import datetime
import logging
from modules import path_manager

def update_time_data():
    """Pobiera aktualny czas i datę, a następnie zapisuje je do pliku JSON."""
    now = datetime.datetime.now()
    weekdays = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

    time_data = {
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%d.%m.%Y"),
        "weekday": weekdays[now.weekday()]
    }

    file_path = os.path.join(path_manager.CACHE_DIR, 'time.json')
    try:
        # Zapewnia, że katalog docelowy istnieje (dodatkowe zabezpieczenie)
        os.makedirs(path_manager.CACHE_DIR, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(time_data, f, ensure_ascii=False, indent=4)
        logging.debug(f"Pomyślnie zapisano dane czasu w {file_path}")
    except IOError as e:
        # Ten błąd nie powinien już występować, ale zostawiamy na wszelki wypadek
        logging.error(f"Nie udało się zapisać danych czasu do {file_path}: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    update_time_data()
    print(f"Plik 'time.json' został zaktualizowany w '{path_manager.CACHE_DIR}'.")
