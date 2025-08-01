# Konfiguracja Synchronizacji Czasu (systemd-timesyncd)

Dokładność wyświetlanego czasu na dashboardzie zależy w 100% od poprawności zegara systemowego urządzenia (Raspberry Pi). Domyślnie, system Raspberry Pi OS używa usługi `systemd-timesyncd` do automatycznej synchronizacji czasu z publicznymi serwerami NTP (Network Time Protocol).

W większości przypadków domyślna konfiguracja jest w pełni wystarczająca. Ten poradnik jest przeznaczony dla zaawansowanych użytkowników, którzy chcą używać własnych, specyficznych serwerów NTP (np. lokalnego serwera w sieci domowej lub preferowanych serwerów publicznych).

## Krok 1: Edycja pliku konfiguracyjnego

Konfiguracja usługi `systemd-timesyncd` znajduje się w pliku `/etc/systemd/timesyncd.conf`. Aby go edytować, użyj edytora tekstu z uprawnieniami administratora, na przykład `nano`:

```bash
sudo nano /etc/systemd/timesyncd.conf
```

## Krok 2: Ustawienie własnych serwerów NTP

W otwartym pliku znajdź sekcję `[Time]`. Domyślnie wygląda ona mniej więcej tak:

```ini
[Time]
#NTP=
#FallbackNTP=0.debian.pool.ntp.org 1.debian.pool.ntp.org 2.debian.pool.ntp.org 3.debian.pool.ntp.org
#RootDistanceMaxSec=5
#PollIntervalMinSec=32
#PollIntervalMaxSec=2048
```

Aby ustawić własne serwery, odkomentuj (usuń `#` na początku) linię `NTP=` i wpisz adresy swoich serwerów, oddzielając je spacjami.

**Przykład:** Użycie polskich, publicznych serwerów czasu z Głównego Urzędu Miar:

```ini
[Time]
NTP=tempus1.gum.gov.pl tempus2.gum.gov.pl
#FallbackNTP=0.debian.pool.ntp.org 1.debian.pool.ntp.org 2.debian.pool.ntp.org 3.debian.pool.ntp.org
...
```

Po dokonaniu zmian zapisz plik i zamknij edytor (w `nano`: `Ctrl+X`, następnie `Y` i `Enter`).

## Krok 3: Restart usługi

Aby zmiany weszły w życie, musisz zrestartować usługę `systemd-timesyncd`:

```bash
sudo systemctl restart systemd-timesyncd
```

## Krok 4: Weryfikacja konfiguracji

Aby sprawdzić, czy usługa poprawnie używa Twoich nowych serwerów, wykonaj komendę:

```bash
timedatectl timesync-status
```

W odpowiedzi powinieneś zobaczyć adresy serwerów, które wpisałeś w pliku konfiguracyjnym, np.:

```
Server: 194.146.251.100 (tempus1.gum.gov.pl)
...
```

Jeśli tak jest, konfiguracja została zakończona pomyślnie.
