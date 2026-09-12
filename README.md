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
- Aktualizator pobiera publiczne wydania z GitHub Releases i przed instalacją sprawdza SHA-256 paczki.

## Instalacja gotowego wydania

1. Pobierz `zorin-shot-X.Y.Z.zip` z GitHub Releases.
2. Rozpakuj paczkę.
3. Uruchom `install.sh`.
4. Instalator pokaże popup z prośbą o wylogowanie i ponowne zalogowanie. Nie trzeba później wpisywać `gnome-extensions enable` ani `gnome-extensions prefs`.

Po pierwszym ponownym logowaniu aplikacja Zorin Shot otworzy się automatycznie. Później uruchamia się ją normalnie z menu aplikacji.

## Jak działa screenshot

W domyślnym trybie `native` rozszerzenie otwiera `Main.screenshotUI` GNOME Shell 46 i wymusza start w trybie **Obszar**. Quick Settings nie jest zamykane przed otwarciem selektora: GNOME najpierw zamraża aktualny stage, a dopiero potem zamyka popupy, więc na zamrożonym obrazie może pozostać otwarte menu. Po wykonaniu zrzutu Zorin Shot odbiera sygnał `screenshot-taken` i otwiera gotowy PNG we własnym edytorze.

## Jak działa aktualizator

Paczka budowana przez GitHub Actions zawiera w `app/build-info.json` nazwę **tego konkretnego repozytorium GitHub**. Nie trzeba wpisywać właściciela repo ręcznie.

Aplikacja odpytuje endpoint `releases/latest`, odczytuje tag wersji i changelog z opisu wydania. Jeśli jest nowsza wersja, pobiera asset `zorin-shot-X.Y.Z.zip`, sprawdza jego SHA-256 i uruchamia instalator w trybie aktualizacji. Ustawienia użytkownika są zachowywane, poza jednorazową migracją trybu screenshotu w 0.2.0 do natywnego selektora GNOME.

Repozytorium powinno być publiczne, jeśli aktualizacje mają działać bez tokena GitHub na komputerze użytkownika.

## Repozytorium i GitHub Actions

Projekt jest gotowy do wrzucenia jako pojedyncze repozytorium. Workflow znajduje się w `.github/workflows/build-release.yml`.

Na każdym pushu do `master` lub `main` GitHub Actions sprawdza składnię Pythona i JavaScript, waliduje schema GSettings, buduje ZIP, generuje `SHA256SUMS` i udostępnia wynik jako artifact workflow. Repozytorium docelowe to `ILoveMyProjects/ZorinShot`.

Po wypchnięciu tagu `vX.Y.Z`, zgodnego z plikiem `VERSION`, workflow dodatkowo tworzy GitHub Release i publikuje `zorin-shot-X.Y.Z.zip` oraz `SHA256SUMS`. Opis Release jest pobierany z odpowiedniej sekcji `CHANGELOG.md`; ten sam tekst pojawia się później w zakładce **Aktualizacje**.

## Struktura

- `extension/zorin-shot@local/` — rozszerzenie GNOME Shell 46;
- `app/zorin-shot-editor.py` — edytor adnotacji;
- `app/zorin-shot-control.py` — Ustawienia / O programie / Aktualizacje;
- `app/i18n.py` — tłumaczenia PL/EN;
- `install.sh` — instalacja i tryb aktualizacji;
- `uninstall.sh` — odinstalowanie;
- `tools/build_release.py` — przygotowanie release ZIP;
- `.github/workflows/build-release.yml` — CI/release;
- `VERSION` — wersja programu;
- `CHANGELOG.md` — changelog używany również przez GitHub Release.

## Zależności na Zorin OS 18

Instalator sprawdza Python 3, PyGObject, Cairo i GTK4. Jeśli bibliotek brakuje, wyświetla informację o wymaganych pakietach.

## Odinstalowanie

Uruchom `uninstall.sh` z rozpakowanej paczki projektu/wydania.
