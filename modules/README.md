# Moduły Aplikacji

Ten katalog zawiera kluczowe moduły logiczne aplikacji, które są odpowiedzialne za zbieranie i przetwarzanie danych.

## Główne Moduły

- `weather.py`: Odpowiada za pobieranie, przetwarzanie i dostarczanie danych pogodowych. Szczegółowy opis znajduje się w pliku README_weather.md.
- `google_calendar.py`: Zarządza całą interakcją z API Kalendarza Google, w tym autoryzacją i pobieraniem wydarzeń. Szczegółowy opis znajduje się w pliku README_google_calendar.md.
- `time.py`: Prosty moduł do pobierania i formatowania aktualnego czasu i daty z zegara systemowego. Instrukcje dotyczące konfiguracji synchronizacji czasu systemowego znajdują się w głównym pliku `README_systemd_time.md`.
- `display.py`: Główny moduł renderujący, który składa obraz z poszczególnych paneli i wysyła go do wyświetlacza e-ink.
- `layout.py`: Wczytuje i parsuje plik `layout.yaml`, definiujący układ paneli na ekranie.
- `drawing_utils.py`: Zestaw funkcji pomocniczych do rysowania, wczytywania czcionek i renderowania ikon SVG.
