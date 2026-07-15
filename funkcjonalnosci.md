### 1. Zaawansowane Odtwarzanie i Synchronizacja (Dual Player)
* **Odtwarzanie dwóch wideo jednocześnie:** Możliwość załadowania dwóch plików wideo (np. wersji *Acceptance* oraz *Emission*) obok siebie.
* **Pełna synchronizacja odtwarzania:** Wspólne odtwarzanie, pauzowanie oraz przewijanie obu plików jednocześnie.
* **Kompensacja opóźnień (Trim / Offset):** Możliwość dokładnego przesunięcia czasowego jednego z wideo (w przód lub w tył), aby idealnie wyrównać klatki obu plików.
* **Precyzyjna nawigacja klatkowa:** Możliwość analizy wideo i przesuwania się dokładnie klatka po klatce.

### 2. Zautomatyzowany Audyt QA (PS Auto-Check)
* **Analiza nazewnictwa plików:** Automatyczne pobieranie metadanych z samej nazwy pliku wideo (np. kod języka, wymiary filmu).
* **Inteligentne parsowanie Briefów (Copydeck):** Moduł czytający pliki `.xlsx` i wyciągający dla danego języka specyficzne wymogi (np. *Rating*, *Age*, *Bing*, *Bong*, *PHNL*) – odporny na różnice w formatowaniu (np. brak ratingu w wersjach niemieckich).
* **Ekstrakcja ukrytych grafik z Excela:** Zaawansowany algorytm potrafiący "wyciągnąć" zagnieżdżone w pliku Excel miniatury (np. ikony ratingowe).
* **Wizualna walidacja wideo (OpenCV):** Automatyczne skanowanie klatek filmu w celu weryfikacji, czy wymagane assety (logotypy *Bing/Bong*, ikony wiekowe pobrane z dysku sieciowego) znajdują się we właściwym miejscu na ekranie.

### 3. Narzędzia do Wizualnej Kontroli Jakości 
* **Wipe / Diff View (Podział ekranu):** Tryb nakładający oba filmy na siebie z interaktywnym suwakiem, pozwalający płynnie odkrywać różnice między wersją A i B.
* **Heatmapa różnic:** Automatyczne zaznaczanie różnic w pikselach między filmami (z podziałem na pewne różnice i potencjalne obszary do sprawdzenia).
* **Interaktywna Pipeta (Eyedropper):** Pobieranie dokładnego koloru (HEX/RGB) z dowolnego punktu w kadrze, na każdym z odtwarzaczy z osobna, co ułatwia weryfikację Brand Guidelines.
* **Linijka (Ruler):** Możliwość rysowania linii pomiarowych i osi na ekranie, by zweryfikować układ, marginesy i zgodność z Safe Zone.

### 4. Analiza i Porównywanie Tekstów (Moduł OCR)
* **Wyciąganie tekstu z wideo na żywo:** Możliwość zaznaczenia myszką wybranego obszaru ekranu w celu odczytania zawartego tam tekstu za pomocą wbudowanego silnika OCR.
* **Niezależne ścieżki weryfikacji:** Obsługa osobnych wycinków tekstowych dla filmów *Acceptance* oraz *Emission*.
* **Porównywanie z Copydeckiem (Briefem):** Wyświetlanie w aplikacji linijek tekstu wyciągniętych prosto z arkusza kalkulacyjnego i zestawianie ich z tekstem zczytanym z obrazu wideo, co przyspiesza kontrolę poprawności literówek.

### 5. Aspekty Techniczne, Architektura i Środowisko Pracy
* **Gotowa Wersja Desktopowa:** Całe narzędzie skompilowane w formie łatwej do instalacji na macOS aplikacji (plik `.dmg`), niewymagającej skomplikowanej konfiguracji po stronie zespołu.
* **Zgodność ze środowiskiem korporacyjnym:** Bezpośrednie podpięcie (łączenie "w locie") z firmowym dyskiem sieciowym zawierającym referencyjne assety graficzne, co chroni przed gromadzeniem przestarzałych plików lokalnie na stacjach roboczych.

### 6. Bezpieczeństwo i Całkowita Hermetyczność (Offline by Design)
* **W 100% lokalne przetwarzanie danych:** Aplikacja działa wyłącznie w środowisku wewnętrznym komputera użytkownika i sieci firmowej. 
* **Zero Cloud & Zero Uploads:** Żadne wgrywane pliki (zarówno materiały wideo, jak i poufne briefy `.xlsx`) nie są wysyłane na zewnętrzne serwery, do chmur obliczeniowych czy usług firm trzecich. Cała ciężka analiza, włączając w to rozpoznawanie obrazu i tekstu (OCR), odbywa się lokalnie na urządzeniu pracownika. Gwarantuje to pełne bezpieczeństwo projektów będących przed oficjalną premierą.
