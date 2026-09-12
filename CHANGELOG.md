# Changelog

Wszystkie istotne zmiany Zorin Shot są opisywane w tym pliku. Sekcja odpowiadająca tagowi wersji jest automatycznie używana jako opis GitHub Release i wyświetlana w zakładce **Aktualizacje** aplikacji.

## [0.3.9] - 2026-09-12

### Dodano
- GitHub Actions generuje stabilny `update.json` z numerem wersji, bezpośrednim URL paczki, SHA-256, kompatybilnością GNOME 46 i changelogiem.
- Po utworzeniu tagu `vX.Y.Z` workflow tworzy/aktualizuje GitHub Release, publikuje ZIP i `SHA256SUMS`, a następnie zapisuje `update.json` na domyślnej gałęzi.
- Dodano `package.sh` do lokalnego zbudowania dokładnie tej samej paczki co w GitHub Actions.
- Dodano `update.json.example` dokumentujący format manifestu.

### Zmieniono
- Updater Zorin Shot najpierw korzysta ze stabilnego `update.json`, podobnie jak ZorinTinyResourceMonitor.
- GitHub Releases API pozostaje jako automatyczny fallback, jeśli manifest jest chwilowo niedostępny.
- Paczka Release zawiera w `build-info.json` repozytorium, domyślną gałąź oraz adres manifestu aktualizacji.

### Bezpieczeństwo
- Updater wymaga prawidłowego SHA-256 z manifestu lub `SHA256SUMS` przed uruchomieniem instalatora.
- Manifest jest walidowany pod kątem UUID, wersji, HTTPS i zgodności z GNOME Shell 46.

## [0.3.8] - 2026-09-12

### Naprawiono
- Usunięto błędne powiązanie pionowej pozycji prawego panelu z pionowym wycentrowaniem obrazu. **Tools / Tool options / Elements / Image details** są teraz zakotwiczone u góry sidebara od pierwszej klatki, niezależnie od rozmiaru screenshotu i poziomu zoomu.
- Naprawiono opóźnione pojawianie się prawego panelu po otwarciu edytora.
- Mały, wycentrowany screenshot nie przesuwa już panelu Tools na środek okna; powiększanie obrazu nie zmienia pionowej pozycji sidebara.

## [0.3.7] - 2026-09-12

### Naprawiono
- Prawy panel nie ma już stałej sztucznej przerwy 18 px u góry. Początek sekcji **Tools** jest dynamicznie synchronizowany z faktyczną górną krawędzią wycentrowanego obrazu.
- Ujednolicono tło całej prawej kolumny, włącznie z viewportem przewijania i obszarem pod nagłówkami sekcji. Nie ma już dwóch różnych odcieni pod `Tools`, `Tool options`, `Elements` i `Image details`.
- Nagłówki sekcji mają przezroczyste tło i dziedziczą dokładnie ten sam kolor co reszta sidebara.

## [0.3.6] - 2026-09-12

### Zmieniono
- Okno potwierdzenia zamknięcia ma teraz wycentrowany układ: ikonę, pytanie, opis, checkbox **Nie pytaj ponownie** i trzy równe przyciski na środku.
- Przyciski zamknięcia są czytelnie rozróżnione: **Anuluj**, **Kopiuj i zamknij** oraz **Zamknij**.

### Naprawiono
- Przywrócono pionowe i poziome centrowanie obrazu w obszarze roboczym, tak jak przed zmianą z wersji 0.3.5.

## [0.3.5] - 2026-09-12

### Naprawiono
- Naprawiono przycisk **Fit / Dopasuj**: przy każdym użyciu ponownie odczytuje rzeczywisty rozmiar viewportu po zmianie rozmiaru lub maksymalizacji okna.
- Obraz jest teraz wyrównany od góry do tej samej linii co panel **Tools**, zamiast zmieniać pionowe położenie przez centrowanie.

### Dodano
- **Ctrl + kółko myszy** nad obrazem powiększa i pomniejsza zoom.

### Zmieniono
- Nagłówki **Tools**, **Tool options**, **Elements** i **Image details** nie są już częścią obramowanej karty. Są zwykłymi nagłówkami z paddingiem, a ramka obejmuje tylko zawartość sekcji.
- Usunięto ciemniejszy pasek/tło bezpośrednio pod nagłówkami sekcji.
- Prawy panel i górna krawędź obrazu zaczynają się na tej samej wysokości.
- Tool Options pozostaje dynamiczne i używa naturalnej wysokości aktywnych opcji.

## [0.3.4] - 2026-09-12

### Naprawiono
- Komunikat instalacyjny / welcome popup korzysta teraz z wykrytego języka systemu: angielski system dostaje komunikaty po angielsku, polski po polsku.
- Usunięto białe linie łączące kolejne znaczniki **Number**. Przyczyną był pozostający w Cairo aktywny path pomiędzy kolejnymi okręgami; każda adnotacja ma teraz izolowaną ścieżkę rysowania.
- Motyw **Ciemny / Jasny / Systemowy** działa również w samym edytorze i zmienia się na żywo, gdy ustawienie zostanie przełączone w centrum Zorin Shot.
- Dodano poprawny padding i wspólne karty dla sekcji **Tools**, **Tool Options**, **Elements** i **Image details**, aby nagłówki nie dotykały krawędzi sekcji.

### Zmieniono
- **Pióro** jest teraz pierwszym narzędziem na liście i domyślnie aktywnym po otwarciu edytora.
- Sidebar w ciemnym motywie korzysta z ciemniejszych kolorów, a obszar roboczy i karty są spójne z wybranym motywem.

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
