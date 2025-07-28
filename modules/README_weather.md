# Moduł: Pogoda

Ten moduł odpowiada za pobieranie, przetwarzanie i dostarczanie danych pogodowych dla dashboardu.

## Funkcjonalność

- **Źródło Danych**: Pobiera aktualne dane synoptyczne z publicznego API Instytutu Meteorologii i Gospodarki Wodnej (IMGW).
- **Wschód i Zachód Słońca**: Oblicza dokładne godziny wschodu i zachodu słońca dla podanej lokalizacji geograficznej, wykorzystując bibliotekę `astral`.
- **Inteligentne Mapowanie Ikon**:
  - Na podstawie danych o zachmurzeniu i opadach, moduł wybiera odpowiednią ikonę pogody.
  - Automatycznie rozróżnia ikony dzienne i nocne na podstawie godzin wschodu/zachodu słońca.
  - Posiada mechanizm awaryjny – jeśli preferowana ikona (np. dzienna) nie istnieje w zasobach, spróbuje użyć jej nocnego odpowiednika.
- **Odporność na Błędy**: W przypadku problemów z API IMGW lub błędów przetwarzania, moduł dostarcza dane zastępcze, aby aplikacja mogła działać dalej. Posiada również mechanizm ponawiania prób przy problemach z siecią.

## Konfiguracja

Konfiguracja tego modułu odbywa się w głównym pliku `config.py`.

1.  **`IMGW_STATION_NAME`**: Nazwa stacji synoptycznej, z której mają być pobierane dane. Musi dokładnie odpowiadać nazwie z API.
    - **Jak znaleźć nazwę?** Wejdź na https://danepubliczne.imgw.pl/api/data/synop, znajdź najbliższą stację i skopiuj wartość z pola `"stacja"`.

2.  **`LOCATION_LAT` i `LOCATION_LON`**: Twoja szerokość i długość geograficzna. Są one **niezbędne** do prawidłowego obliczenia godzin wschodu i zachodu słońca, co z kolei wpływa na wybór ikon dziennych/nocnych.

## Silnik Reguł Ikon

Wewnątrz pliku `weather.py`, zmienna `WEATHER_RULES` definiuje logikę wyboru ikon. Jest to lista reguł, gdzie każda reguła sprawdza określony warunek (np. `suma_opadu > 0`). Pierwsza spełniona reguła determinuje, która ikona zostanie użyta. Możesz modyfikować lub dodawać nowe reguły, jeśli chcesz dostosować mapowanie ikon do swoich potrzeb.
