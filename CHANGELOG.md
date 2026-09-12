# Changelog

Wszystkie istotne zmiany Zorin Shot są opisywane w tym pliku. Sekcja odpowiadająca tagowi wersji jest automatycznie używana jako opis GitHub Release i wyświetlana w zakładce **Aktualizacje** aplikacji.

## [0.2.0] - 2026-09-12

### Naprawiono
- Dodawanie przycisku Zorin Shot do właściwego paska akcji Quick Settings w GNOME Shell 46; przycisk jest wstawiany bezpośrednio po oryginalnym przycisku zrzutu ekranu. Dodano również awaryjne wyszukiwanie oryginalnego przycisku w drzewie Quick Settings dla zmodyfikowanych buildów Zorin.
- Domyślny screenshot Zorin Shot otwiera teraz **natywny selektor GNOME** — obszar / okno / ekran — zamiast najpierw otwierać w edytorze obraz całego pulpitu.
- Po zakończeniu wyboru w natywnym selektorze GNOME wynik jest automatycznie przekazywany do edytora Zorin Shot.
- Cenzura jest teraz w 100% nieprzezroczysta i całkowicie zasłania wskazany obszar.
- Identyfikatory aplikacji i plików `.desktop` zostały rozdzielone i dopasowane (`io.local.ZorinShot.Control` / `io.local.ZorinShot.Editor`), aby GNOME poprawnie wiązał okna z ikoną Zorin Shot zamiast ikony zastępczej.
- Instalator instaluje zarówno zwykłą, jak i symboliczną ikonę Zorin Shot oraz odświeża cache ikon.

### Dodano
- Wybór języka **Polski / English** w Ustawieniach Zorin Shot.
- Tłumaczenia centrum Zorin Shot, edytora oraz komunikatów rozszerzenia.
- Migrację starszego trybu przechwytywania do natywnego selektora GNOME podczas aktualizacji do 0.2.0.

## [0.1.0] - 2026-09-12

### Dodano
- Własny przycisk Zorin Shot obok oryginalnego przycisku zrzutu ekranu GNOME.
- Przechwytywanie aktualnego stanu powłoki przed otwarciem edytora.
- Tryby: obszar, cały widoczny pulpit i aktywne okno.
- Wbudowany edytor: pióro, marker, strzałka, prostokąt, elipsa, tekst, cenzura, kadrowanie, undo/redo, zoom, kopiowanie i zapis PNG.
- Przejęcie `Print Screen` przez Zorin Shot z pozostawieniem oryginalnego panelu GNOME pod `Super + Print Screen`.
- Centrum Zorin Shot z zakładkami **Ustawienia**, **O programie** i **Aktualizacje**.
- Sprawdzanie najnowszej wersji z GitHub Releases, wyświetlanie changelogu i aktualizacja bez wpisywania poleceń w terminalu.
- Walidacja SHA-256 pobranej paczki aktualizacji.
- Automatyczne budowanie paczki w GitHub Actions i publikowanie jej przy tagach `vX.Y.Z`.
