# Podsumowanie Wdrożeń – Feedback QA (Sync DualPlayer v2.3)

Poniżej znajduje się kompletne zestawienie wszystkich poprawek i nowych funkcji wprowadzonych do aplikacji na podstawie ostatniego feedbacku od zespołu QA. Prace zostały zrealizowane etapami, a wszystkie zmiany są już zintegrowane w paczce `Sync_DualPlayer_v2.3.dmg`.

---

## 🎨 Etap 1: Interfejs i UX (Quick Wins)
Skupiliśmy się na najszybszych i najbardziej użytecznych zmianach wizualnych.
* **Tryb Ciemny/Jasny (Dark/Light Mode):** Wprowadzono pełny przełącznik motywu w głównym oknie aplikacji. Tryb ciemny jest teraz zoptymalizowany pod kątem mniejszego zmęczenia wzroku podczas długich sesji audytu wideo.

## 📝 Etap 2: Raporty i Nomenklatura
Poprawki mające na celu ułatwienie generowania raportów i wprowadzania własnych nazw bez naruszania struktury aplikacji.
* **Edytowalne Nazwy Wideo:** Zachowano domyślne podpisy ("Acceptance" i "Emission"), ale wprowadzono wokół nich pola tekstowe. Użytkownik może teraz swobodnie kliknąć i wpisać własne nazwy (np. konkretne kody plików), które będą odzwierciedlane w aplikacji i (w przyszłości) na generowanych raportach.

## 🔍 Etap 3: Narzędzie Różnic (Heatmapa i Diff)
Rozbudowa narzędzia weryfikacji pikselowej, aby ułatwić wychwytywanie drobnych błędów.
* **Tryb Heatmapy (Wipe / Heatmap):** Dodano przełącznik w pasku narzędzi pozwalający na wybór trybu wyświetlania różnic. Zamiast dzielenia ekranu na pół (Wipe), dostępny jest teraz tryb "Heatmap".
* **Warstwowanie Obrazu:** W trybie Heatmapy wyświetlany jest film *Emission* z nałożoną półprzezroczystą czarną maską, a same różnice świecą się jaskrawo na wierzchu, co błyskawicznie wskazuje rozbieżności.
* **Suwak Ściemniania (Opacity):** Zoptymalizowano UI przenosząc nowy, krótszy suwak "Ściemnienie (Opacity)" na górny pasek narzędzi obok przycisku odświeżania. Domyślne krycie ustawiono na optymalne 75%.
* **Responsywność (max-h 60vh):** Ograniczono wysokość sekcji Diff do 60% wysokości ekranu, dzięki czemu narzędzie idealnie mieści się na mniejszych ekranach Macbooków bez konieczności scrollowania.
* **Optymalizacja Wydajnościowa:** Maska przyciemniająca jest realizowana sprzętowo, nie obciążając głównego wątku (Web Workera) odpowiedzialnego za wyliczanie różnic pikselowych, z myślą o procesorach M1.

## 🛠️ Etap 4: Techniczne, Wydajnościowe i Zamykanie Aplikacji
Rozwiązanie dwóch najbardziej uciążliwych problemów technicznych (backend i macOS wrapper).
* **Fix: Kompresja i Spadki Rozdzielczości Wideo (VideoToolbox):** Rozwiązano problem zniekształcania filmów `.mov` (np. skalowania ProRes z 1080p do 720p). Limit kompresji `h264_videotoolbox` został drastycznie podniesiony (z 3 Mbps do 15 Mbps z flagą utrzymania jakości). Filmy zachowują teraz natywną rozdzielczość i kryształową jakość, nie obciążając przy tym sprzętowego kodera w procesorach M1.
* **Fix: Błąd Zamykania (Wymagany Force Quit):** Przepisano główny plik rozruchowy aplikacji dla macOS. Zastąpiono prosty skrypt C pełnoprawnym, minimalistycznym wrapperem w `Objective-C` wykorzystującym środowisko `Cocoa`. Dzięki temu aplikacja zaczęła "rozumieć" język systemu operacyjnego – prawidłowo nasłuchuje zdarzeń zamknięcia (np. użycia `CMD+Q` czy zamykania całego komputera) i samoczynnie bez zawieszeń ubija wszystkie procesy serwerowe w tle. Zniknął przymus "Wymuszania Zakończenia".

---
*Gotowa paczka `.dmg` znajduje się w katalogu głównym i jest gotowa do testów przez zespół!*
