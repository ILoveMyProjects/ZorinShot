# Test plan — Zorin Shot 0.2.0

Po instalacji na Zorin OS 18 / GNOME Shell 46 i ponownym zalogowaniu sprawdź kolejno:

1. Otwórz Quick Settings. Oryginalna ikona screenshotu nadal istnieje, a **bezpośrednio obok niej** znajduje się nowa ikona Zorin Shot.
2. Kliknij starą ikonę: powinien otworzyć się oryginalny panel screenshot/nagrywanie GNOME.
3. Kliknij nową ikonę Zorin Shot przy domyślnym trybie `Selektor GNOME`.
4. Powinien otworzyć się **natywny screenshot UI GNOME**, w którym można wybrać obszar, okno lub ekran. Edytor Zorin Shot nie powinien otwierać wcześniej całego pulpitu.
5. Zrób zrzut wybranego obszaru. Dopiero po wykonaniu zrzutu powinien otworzyć się edytor Zorin Shot z wybranym fragmentem.
6. Sprawdź Pióro, Marker, Strzałkę, Prostokąt, Elipsę, Tekst i Cenzurę.
7. Cenzura ma być **w 100% nieprzezroczysta** — piksele pod zaznaczeniem nie mogą prześwitywać.
8. Sprawdź Cofnij / Ponów, `Ctrl+C` oraz `Ctrl+S`.
9. `Print Screen` powinien otworzyć Zorin Shot / natywny selektor GNOME, a `Super+Print Screen` oryginalny panel GNOME.
10. Uruchom `Zorin Shot` z menu aplikacji. Okno powinno być powiązane z ikoną Zorin Shot, a nie z ogólną ikoną rozszerzeń/puzzla.
11. W Ustawieniach wybierz `English`; etykiety centrum Zorin Shot mają natychmiast przełączyć się na angielski. Nowo otwarty edytor i komunikaty rozszerzenia też mają używać angielskiego.
12. Wróć na `Polski` i powtórz test.
13. Ustaw `Cały pulpit bez pytania` oraz `Aktywne okno bez pytania` i sprawdź oba opcjonalne tryby.
14. Wyłącz rozszerzenie. Oryginalny skrót screenshotu powinien zostać przywrócony.
