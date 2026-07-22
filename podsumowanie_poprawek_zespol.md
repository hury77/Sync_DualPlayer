# Podsumowanie Zmian w Odtwarzaczu (Wydanie: Wczoraj Wieczór - Dzisiaj) 🚀

Poniżej znajduje się kompletna lista wszystkich poprawek i nowych funkcjonalności wprowadzonych od wczorajszego wieczora na prośbę zespołu QA. 

Zmiany podzieliłem na dwie kategorie: UI/UX (Poprawki) oraz Nowe Funkcjonalności (Analiza).

## 🛠️ Poprawki Interfejsu i Narzędzi (UI/UX)

1. **Powiększone fonty czasówek**
   Zwiększono rozmiar czcionki (o 2 punkty) dla liczników czasu (timecode) wyświetlanych nad suwakami głośności. Są one teraz znacznie bardziej czytelne z większej odległości.

2. **Czytelne nazewnictwo źródeł (Single Player)**
   Zamiast technicznych nazw "Acceptance" i "Emission", przyciski zmiany źródła w trybie pojedynczego odtwarzacza wyświetlają teraz domyślnie **"Video 1" / "Video 2"**, a po wgraniu własnych plików – dokładne nazwy wgranych wideo.

3. **Poprawna nawigacja po osi w trybie Heatmapy**
   Naprawiono błąd, który sprawiał, że po kliknięciu na czerwony/żółty znacznik usterki na osi czasu, różnice nie podświetlały się automatycznie na Heatmapie. Teraz kliknięcie przenosi dokładnie w miejsce usterki i od razu rysuje czerwoną poświatę.

4. **Bardziej naturalne zachowanie Linijki (Ruler)**
   Linijka wymaga teraz intuicyjnego gestu "kliknij, przeciągnij i upuść" aby narysować pełną linię. Wyeliminowano irytujący błąd, który powodował stawianie bezużytecznych "kropek" (pojedynczych kliknięć).

5. **Uporządkowany Kroplomierz (Eyedropper)**
   Usunięto rozpraszające okienko z podglądem RGB/HEX, które stale było przyklejone do kursora myszki po aktywacji narzędzia. Obecnie kroplomierz zostawia po kliknięciu precyzyjny celownik (crosshair) z przypiętą informacją o kolorze badanego piksela.

6. **Lepsza czytelność modułu OCR**
   We wszystkich polach podglądu wyciągniętego tekstu (OCR) oraz w module wklejania "Copydecku" zamieniono czcionkę maszynową (`font-mono`) na nowoczesny krój bezszeryfowy (`font-sans`). Problem mylenia litery "O" z cyfrą "0" oraz "I" z "l" został całkowicie wyeliminowany, co pozwala na szybszy *double-check* tekstów.

7. **Uporządkowany panel UI**
   Usunięto zduplikowany suwak przezroczystości (opacity) dla trybu Heatmapy, który niepotrzebnie zaśmiecał panel narzędzi. 

---

## 🔬 Nowe Funkcjonalności Detekcji (Diff Mode)

8. **Suwak Czułości Wideo (Sensitivity Slider)**
   Dodano w UI nową kontrolkę rozwijaną ("Niska", "Średnia", "Wysoka"). Pozwala to testerom na samodzielne zbalansowanie algorytmu szukania różnic. 
   - *Wysoka czułość* pozwala wyłapać usterki stanowiące nawet promil powierzchni klatki (np. ukryty znak wodny na ułamek sekundy).
   - *Niska czułość* pozwala odfiltrować fałszywe alarmy spowodowane ciężką kompresją wideo w słabej jakości plikach.

9. **Detekcja Rozjazdów Dźwięku na żywo (Audio Diff)**
   Największa innowacja dzisiejszego wydania. Aplikacja w trybie *Diff Mode* równolegle z obrazem analizuje fale dźwiękowe z obu odtwarzaczy za pomocą natywnego *Web Audio API* (analiza częstotliwości FFT). 
   - Gdy aplikacja wykryje nagły brak spójności w głośności lub barwie dźwięku, natychmiast wygeneruje ostrzegawczy **Niebieski Znacznik na osi czasu**.
   - Obok przycisków odtwarzania włączy się na ułamek sekundy pulsujący czerwony znak z napisem `Audio Diff!`.
   - Moduł działa bezpośrednio na sprzęcie (blisko rdzenia procesora), więc nie powoduje żadnych spadków wydajności w analizie samego obrazu.

---
*Najnowsza wersja instalacyjna (DMG) zawierająca wszystkie powyższe usprawnienia została wygenerowana ze statusem "Sukces" i jest gotowa do pobrania.*
