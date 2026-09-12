# Changelog

Wszystkie istotne zmiany Zorin Shot są opisywane w tym pliku. Sekcja odpowiadająca tagowi wersji jest automatycznie używana jako opis GitHub Release i wyświetlana w zakładce **Aktualizacje** aplikacji.

## [0.3.3] - 2026-09-12

### Zmieniono
- **Tools** zawiera teraz wyłącznie kompaktowe ikony bez napisów; są rozmiarem zbliżone do ikon z górnego paska, a nazwa narzędzia jest dostępna w tooltipie.
- Dodano własny, spójny zestaw ikon symbolicznych dla narzędzi Zorin Shot zamiast dużych znaków tekstowych/emoji.
- Górny pasek został uporządkowany w grupy: historia/edycja → zoom → kopiowanie/zapis.
- Ciemny motyw używa teraz ciemnego obszaru roboczego i sidebara bardziej zbliżonego kolorystycznie do Zorin Dark; jasny motyw zachowuje jasne tło.
- **Tool Options** ma niejednorodny, dynamiczny rozmiar i zajmuje tylko tyle wysokości, ile potrzebuje aktualne narzędzie.
- **Elements** rośnie wraz z zawartością tylko do ustalonego maksimum, po czym automatycznie przechodzi w przewijaną listę.

### Dodano
- Przycisk **Ustawienia** w pasku tytułu edytora, bezpośrednio obok systemowych przycisków okna; otwiera to samo centrum Zorin Shot co ikona aplikacji w menu programów.
- Podczas kadrowania wyświetlana jest wyraźna **przerywana ramka** oraz przyciemnienie obszaru, który zostanie odcięty.

### Naprawiono
- Dodatkowo odcięto gest rysowania dla narzędzia **Numer**, aby między kolejnymi numerami nie mogła powstać żadna przypadkowa kreska.
- Ustabilizowano układ prawej kolumny, tak aby zmiana opcji narzędzia nie odsuwała niepotrzebnie sekcji **Elements** i **Image details**.

## [0.3.2] - 2026-09-12

### Dodano
- Nowy wybór motywu aplikacji: **Systemowy / Ciemny / Jasny**.
- Ulepszony wygląd edytora z większymi ikonami narzędzi oraz ciemniejszym sidebarem w stylu zbliżonym do dark Zorin.

### Zmieniono
- Panel narzędzi został wizualnie dopracowany: większe symbole, czytelniejsze kafelki i bardziej nowoczesny układ.
- Sekcja **Opcje narzędzia** jest osadzona bardziej kompaktowo, aby nie tworzyć niepotrzebnych dużych pustych przestrzeni.
- Okno ustawień także respektuje wybrany motyw aplikacji.

### Naprawiono
- Naprawiono błąd narzędzia **Numer**, w którym między kolejnymi numerami pojawiała się niechciana kreska.
- Ustabilizowano dalsze zachowanie prawego panelu podczas pracy narzędziami.

## [0.3.1] - 2026-09-12

### Zmieniono
- Górny pasek edytora używa teraz samych ikon dla: cofnij, ponów, usuń, pomniejsz, powiększ, dopasuj, kopiuj i zapisz.
- Prawa kolumna została ustabilizowana: zawiera tylko **Narzędzia**, **Opcje narzędzia**, **Elementy** i **Szczegóły obrazu**.
- Sekcja **Elementy** ma własny scroll, więc przy większej liczbie adnotacji okno aplikacji nie rozszerza się i obszar obrazu nie zmienia położenia.
- Przy zamykaniu okna pojawia się dialog z opcjami **Anuluj**, **Kopiuj i zamknij** oraz **Zamknij**, a także checkbox **Nie pytaj ponownie**.

### Naprawiono
- Usunięto problem z niestabilnym układem, przez który po zmianach po prawej stronie przesuwał się cały obszar obrazu.
- Poprawiono zachowanie prawego panelu tak, aby nie znikał podczas przełączania narzędzi.
- Poprawiono obsługę listy elementów i zaznaczenia aktywnej adnotacji.

## [0.3.0] - 2026-09-12

### Dodano
- Przebudowany edytor z układem zbliżonym do referencji: duży obszar obrazu po lewej i prawy panel opcji.
- Nowe narzędzia: **Linia**, **Przesuń** (zaznaczanie i przesuwanie elementów) oraz **Numer** do wstawiania kolejnych oznaczeń 1, 2, 3… w kołach.
- Lista elementów po prawej z wyborem aktywnej adnotacji oraz przyciskami usuwania i zmiany kolejności.
- Panel **Szczegóły obrazu** z nazwą pliku, rozmiarem, zoomem i liczbą adnotacji.
- Osobne opcje dla narzędzi: grubość, kolor, przezroczystość, wypełnienie, tło tekstu, promień numerów i rozmiar pikseli cenzury.

### Zmieniono
- Obraz automatycznie dopasowuje się do rozmiaru okna i rośnie wraz z powiększaniem okna; nadal dostępne są ręczne przyciski zoomu i dopasowania.
- Marker używa półprzezroczystego koloru, dzięki czemu tło pozostaje widoczne.
- Cenzura działa teraz jako pikselizacja w kwadratowe bloki zamiast prostego przyciemnienia.
- Tekst i numerowane znaczniki mogą mieć własne tło / wypełnienie z kolorem i przezroczystością.

## [0.2.1] - 2026-09-12

### Naprawiono
- Drugi przycisk Quick Settings jest teraz odnajdywany przez rzeczywisty `SystemItem` GNOME 46 (`quickSettingsItems` / grid), a nie tylko przez prywatne pole; Zorin Shot ponawia wstawienie także przy każdym otwarciu Quick Settings.
- Usunięto popup „nie znaleziono paska akcji Quick Settings”; jeśli Zorin Taskbar przebuduje menu później, rozszerzenie czeka i ponawia integrację.
- Natywny selektor screenshotu zawsze startuje w trybie **Obszar**, zamiast zapamiętanego wcześniej trybu pełnego ekranu.
- Zorin Shot nie zamyka Quick Settings przed zamrożeniem obrazu. GNOME 46 najpierw przechwytuje aktualny stage, a dopiero później zamyka popupy, dzięki czemu można zaznaczyć fragment zawierający otwarte menu.
- Okno Zorin Shot używa teraz `Gtk.Window.set_titlebar()` zamiast wkładać `Gtk.HeaderBar` do treści, co usuwa podwójny pasek tytułu i podwójne przyciski minimalizuj/maksymalizuj/zamknij.
- Ikony aplikacji są instalowane także pod nazwami odpowiadającymi Application ID, aby GTK4/GNOME poprawnie kojarzył okna z ikoną Zorin Shot.
- Usunięto stary dodatkowy plik `zorin-shot-settings.desktop`, który nie jest już potrzebny.
- Pierwszy język jest wykrywany z `LANGUAGE` / `LC_*` / `LANG`: polski dla systemu PL, angielski dla systemu EN i pozostałych. Użytkownik nadal może później ręcznie przełączyć Polski/English.
- Lokalna paczka i updater są teraz na stałe powiązane z `ILoveMyProjects/ZorinShot`.
- GitHub Actions buduje zarówno z gałęzi `master`, jak i `main`.

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
