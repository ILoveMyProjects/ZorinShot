# Zorin Shot

Zorin Shot to narzędzie do zrzutów ekranu przygotowane dla **Zorin OS 18 / GNOME Shell 46**. Składa się z rozszerzenia GNOME Shell, własnego edytora GTK4 oraz aplikacji ustawień/aktualizacji.

## Funkcje

- Oryginalny przycisk aparatu GNOME pozostaje bez zmian: nadal obsługuje systemowy screenshot i nagrywanie ekranu.
- Zorin Shot dodaje drugi przycisk obok niego.
- `Print Screen` może uruchamiać Zorin Shot, a `Super + Print Screen` pozostaje dla oryginalnego panelu GNOME.
- Tryb **Obszar** najpierw przechwytuje aktualny stan powłoki, więc na obrazie mogą zostać zachowane otwarte Quick Settings/menu.
- Tryby: obszar, cały widoczny pulpit i aktywne okno.
- Wbudowany edytor: pióro, marker, strzałka, prostokąt, elipsa, tekst, cenzura, kadrowanie, undo/redo, zoom, kopiowanie i zapis PNG.
- Aplikacja **Zorin Shot** ma zakładki:
  - **Ustawienia** — integracja, tryb przechwytywania, kursor i Print Screen;
  - **O programie** — opis, wersja i link do repozytorium;
  - **Aktualizacje** — aktualna/najnowsza wersja, changelog, ręczne sprawdzanie i instalacja aktualizacji.
- Aktualizator pobiera publiczne wydania z GitHub Releases i przed instalacją sprawdza SHA-256 paczki.

## Instalacja gotowego wydania

1. Pobierz `zorin-shot-X.Y.Z.zip` z GitHub Releases.
2. Rozpakuj paczkę.
3. Uruchom `install.sh`.
4. Instalator pokaże popup z prośbą o wylogowanie i ponowne zalogowanie. Nie trzeba później wpisywać `gnome-extensions enable` ani `gnome-extensions prefs`.

Po pierwszym ponownym logowaniu aplikacja Zorin Shot otworzy się automatycznie. Później uruchamia się ją normalnie z menu aplikacji.

## Jak działa aktualizator

Paczka budowana przez GitHub Actions zawiera w `app/build-info.json` nazwę **tego konkretnego repozytorium GitHub**. Nie trzeba wpisywać właściciela repo ręcznie.

Aplikacja odpytuje endpoint `releases/latest`, odczytuje tag wersji i changelog z opisu wydania. Jeśli jest nowsza wersja, pobiera asset `zorin-shot-X.Y.Z.zip`, sprawdza jego SHA-256 i uruchamia instalator w trybie aktualizacji. Ustawienia użytkownika są zachowywane.

Repozytorium powinno być publiczne, jeśli aktualizacje mają działać bez tokena GitHub na komputerze użytkownika.

## Repozytorium i GitHub Actions

Projekt jest gotowy do wrzucenia jako pojedyncze repozytorium. Workflow znajduje się w:

`.github/workflows/build-release.yml`

Na każdym pushu do `main` GitHub Actions:

- sprawdza składnię Pythona i JavaScript,
- waliduje schema GSettings,
- buduje paczkę ZIP,
- generuje `SHA256SUMS`,
- udostępnia wynik jako artifact workflow.

Gdy wypchniesz tag w formacie `vX.Y.Z` i jest on zgodny z plikiem `VERSION`, workflow dodatkowo tworzy **GitHub Release** i dodaje do niego:

- `zorin-shot-X.Y.Z.zip`,
- `SHA256SUMS`.

Opis Release jest pobierany z odpowiedniej sekcji `CHANGELOG.md`; ten sam tekst pojawia się później użytkownikowi w zakładce **Aktualizacje**.

### Wydanie nowej wersji

Przed wydaniem:

1. zmień numer w `VERSION`, np. `0.2.0`;
2. dodaj sekcję `## [0.2.0] - RRRR-MM-DD` w `CHANGELOG.md`;
3. zatwierdź zmiany w `main`;
4. utwórz tag `v0.2.0` i wyślij go do GitHub.

Resztę wykonuje GitHub Actions.

## Struktura

- `extension/zorin-shot@local/` — rozszerzenie GNOME Shell 46;
- `app/zorin-shot-editor.py` — edytor adnotacji;
- `app/zorin-shot-control.py` — Ustawienia / O programie / Aktualizacje;
- `install.sh` — instalacja i tryb aktualizacji;
- `uninstall.sh` — odinstalowanie;
- `tools/build_release.py` — deterministyczne przygotowanie release ZIP;
- `.github/workflows/build-release.yml` — CI/release;
- `VERSION` — wersja programu;
- `CHANGELOG.md` — changelog używany również przez GitHub Release.

## Zależności na Zorin OS 18

Instalator sprawdza Python 3, PyGObject, Cairo i GTK4. Jeśli bibliotek brakuje, wyświetla informację o wymaganych pakietach.

## Odinstalowanie

Uruchom `uninstall.sh` z rozpakowanej paczki projektu/wydania.
