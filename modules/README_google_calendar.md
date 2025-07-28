# Moduł: Kalendarz Google

Ten moduł jest odpowiedzialny za całą interakcję z API Kalendarza Google.

## Funkcjonalność

- **Autoryzacja OAuth 2.0**: Bezpiecznie zarządza uwierzytelnianiem, odświeżaniem tokenów i obsługą pierwszego logowania.
- **Pobieranie Wydarzeń**: Pobiera wydarzenia z wielu zdefiniowanych w `config.py` kalendarzy (osobisty, święta, nietypowe święta).
- **Przetwarzanie Danych**: Przetwarza surowe dane z API na ustrukturyzowane formaty gotowe do wyświetlenia.
- **Buforowanie**: Zapisuje przetworzone dane w pliku `calendar.json` w katalogu tymczasowym, aby zminimalizować liczbę zapytań do API.
- **Odporność na Błędy**: Wykorzystuje mechanizm ponawiania prób w przypadku przejściowych problemów z siecią.

## Konfiguracja

Konfiguracja tego modułu odbywa się w głównym pliku `config.py`.

1.  **`GOOGLE_CREDS_FILE` i `GOOGLE_TOKEN_FILE`**: Ścieżki do plików poświadczeń. Domyślne wartości są zazwyczaj odpowiednie.

2.  **`GOOGLE_CALENDAR_IDS`**: Słownik, w którym definiujesz, które kalendarze mają być synchronizowane.
    - `'personal'`: Domyślnie ustawiony na `'primary'`, co oznacza główny kalendarz Twojego konta.
    - `'holidays'`: Kalendarz z polskimi świętami.
    - `'unusual'`: Dowolny inny kalendarz. Domyślnie skonfigurowany do wyświetlania nietypowych świąt. Możesz tu wstawić ID dowolnego kalendarza, do którego masz dostęp. ID kalendarza znajdziesz w jego ustawieniach w interfejsie webowym Kalendarza Google.

3.  **`MAX_UPCOMING_EVENTS`**: Liczba nadchodzących wydarzeń osobistych do wyświetlenia na liście.

## Pierwsze Uruchomienie i Autoryzacja

Aby moduł mógł działać, musisz go jednorazowo autoryzować do dostępu do Twojego konta Google.

1.  Pobierz plik `credentials.json` z Google Cloud Console (szczegółowa instrukcja w głównym `README.md`).
2.  Umieść go w głównym katalogu projektu.
3.  Uruchom ten skrypt bezpośrednio z terminala:
    ```bash
    # Będąc w głównym katalogu projektu i aktywnym .venv
    python modules/google_calendar.py
    ```
4.  Postępuj zgodnie z instrukcjami w konsoli, aby otworzyć link w przeglądarce i udzielić zgody. Po pomyślnej autoryzacji zostanie utworzony plik `token.json`.
