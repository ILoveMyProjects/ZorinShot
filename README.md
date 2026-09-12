# Zorin Shot

Zorin Shot to narzędzie do zrzutów ekranu przygotowane dla **Zorin OS 18 / GNOME Shell 46**. Składa się z rozszerzenia GNOME Shell, własnego edytora GTK4 oraz aplikacji ustawień/aktualizacji.

## Funkcje

- Oryginalny przycisk aparatu GNOME pozostaje bez zmian i nadal obsługuje systemowy screenshot oraz nagrywanie ekranu.
- Zorin Shot dodaje **drugi przycisk bezpośrednio obok oryginalnego przycisku screenshotu** w Quick Settings.
- Kliknięcie Zorin Shot domyślnie otwiera **wbudowany selektor screenshotów GNOME**: obszar / okno / ekran. Po wykonaniu zrzutu obraz trafia automatycznie do edytora Zorin Shot.
- `Print Screen` może uruchamiać Zorin Shot, a `Super + Print Screen` pozostaje dla oryginalnego panelu GNOME.
- Opcjonalne tryby bez pytania: cały pulpit i aktywne okno.
- Wbudowany edytor: pióro, marker, strzałka, prostokąt, elipsa, tekst, **całkowicie nieprzezroczysta cenzura**, kadrowanie, undo/redo, zoom, kopiowanie i zapis PNG.
- Interfejs po polsku lub angielsku. Przy pierwszej instalacji język jest automatycznie wykrywany z ustawień systemu, a później można go ręcznie zmienić w Ustawieniach.
- Aplikacja **Zorin Shot** ma zakładki:
  - **Ustawienia / Settings** — integracja, tryb przechwytywania, kursor, Print Screen i język;
  - **O programie / About** — opis, wersja i link do repozytorium;
  - **Aktualizacje / Updates** — aktualna/najnowsza wersja, changelog, ręczne sprawdzanie i instalacja aktualizacji.
- Aktualizator najpierw czyta stabilny `update.json` z repozytorium, a jeśli manifest jest chwilowo niedostępny, używa GitHub Releases API jako fallback. Przed instalacją zawsze sprawdza SHA-256 paczki.

## Instalacja gotowego wydania

1. Pobierz `zorin-shot-X.Y.Z.zip` z GitHub Releases.
2. Rozpakuj paczkę.
3. Uruchom `install.sh`.
4. Instalator pokaże popup z prośbą o wylogowanie i ponowne zalogowanie. Nie trzeba później wpisywać `gnome-extensions enable` ani `gnome-extensions prefs`.

Po pierwszym ponownym logowaniu aplikacja Zorin Shot otworzy się automatycznie. Później uruchamia się ją normalnie z menu aplikacji.

## Jak działa screenshot

W domyślnym trybie `native` rozszerzenie otwiera `Main.screenshotUI` GNOME Shell 46 i wymusza start w trybie **Obszar**. Quick Settings nie jest zamykane przed otwarciem selektora: GNOME najpierw zamraża aktualny stage, a dopiero potem zamyka popupy, więc na zamrożonym obrazie może pozostać otwarte menu. Po wykonaniu zrzutu Zorin Shot odbiera sygnał `screenshot-taken` i otwiera gotowy PNG we własnym edytorze.

## Jak działa aktualizator

Paczka budowana przez GitHub Actions zawiera w `app/build-info.json` nazwę repozytorium `ILoveMyProjects/ZorinShot` oraz adres stabilnego manifestu:

`https://raw.githubusercontent.com/ILoveMyProjects/ZorinShot/master/update.json`

Po kliknięciu **Sprawdź aktualizacje** aplikacja najpierw pobiera ten manifest. `update.json` zawiera numer najnowszej wersji, changelog, bezpośredni URL assetu GitHub Release oraz SHA-256. Jeśli manifest jest niedostępny lub uszkodzony, updater automatycznie przechodzi na GitHub Releases API.

Jeśli jest nowsza wersja, Zorin Shot pobiera `zorin-shot-X.Y.Z.zip`, sprawdza SHA-256, bezpiecznie rozpakowuje paczkę i uruchamia `install.sh --update --no-popup`. Ustawienia użytkownika są zachowywane.

Repozytorium powinno być publiczne, jeśli aktualizacje mają działać bez tokena GitHub na komputerze użytkownika.

## Repozytorium i GitHub Actions

Workflow znajduje się w `.github/workflows/build-release.yml` i działa podobnie do mechanizmu używanego w `ZorinTinyResourceMonitor`.

Na każdym pushu do `master` lub `main` GitHub Actions:

- sprawdza składnię Pythona i JavaScript;
- waliduje schema GSettings i pliki `.desktop`;
- buduje gotowy ZIP;
- generuje `SHA256SUMS`;
- generuje przyszły `update.json`;
- publikuje wszystkie pliki jako artifact workflow.

Po wypchnięciu tagu `vX.Y.Z`, zgodnego z plikiem `VERSION`, workflow dodatkowo:

1. tworzy albo aktualizuje GitHub Release `vX.Y.Z`;
2. wrzuca do Release `zorin-shot-X.Y.Z.zip` oraz `SHA256SUMS`;
3. bierze changelog z odpowiedniej sekcji `CHANGELOG.md`;
4. po utworzeniu Release zapisuje wygenerowany `update.json` na domyślnej gałęzi repozytorium.

Dzięki temu użytkownik z wcześniejszą wersją może wejść w **Zorin Shot → Updates → Check for updates → Download and install update** i wykonać cały update bez terminala.

### Wydanie nowej wersji

1. Zmień `VERSION`, np. na `0.4.0`.
2. Dodaj sekcję `## [0.4.0] - YYYY-MM-DD` w `CHANGELOG.md`.
3. Wypchnij zmiany na `master`.
4. Utwórz i wypchnij tag `v0.4.0`.
5. Resztę wykonuje GitHub Actions.

Workflow potrzebuje uprawnienia `contents: write`, które jest już zadeklarowane w pliku workflow. Jeśli ustawienia repozytorium blokują zapis przez `GITHUB_TOKEN`, w **Settings → Actions → General → Workflow permissions** ustaw **Read and write permissions**.

## Struktura

- `extension/zorin-shot@local/` — rozszerzenie GNOME Shell 46;
- `app/zorin-shot-editor.py` — edytor adnotacji;
- `app/zorin-shot-control.py` — Ustawienia / O programie / Aktualizacje;
- `app/i18n.py` — tłumaczenia PL/EN;
- `install.sh` — instalacja i tryb aktualizacji;
- `uninstall.sh` — odinstalowanie;
- `tools/build_release.py` — przygotowanie release ZIP, SHA-256 i `update.json`;
- `package.sh` — lokalny build tej samej paczki;
- `update.json.example` — przykład manifestu aktualizacji;
- `.github/workflows/build-release.yml` — CI/release;
- `VERSION` — wersja programu;
- `CHANGELOG.md` — changelog używany również przez GitHub Release.

## Zależności na Zorin OS 18

Instalator sprawdza Python 3, PyGObject, Cairo i GTK4. Jeśli bibliotek brakuje, wyświetla informację o wymaganych pakietach.

## Odinstalowanie

Uruchom `uninstall.sh` z rozpakowanej paczki projektu/wydania.
