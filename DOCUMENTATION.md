# Sync DualPlayer - Dokumentacja Techniczna i Instrukcja Obsługi

## 1. Wstęp
**Sync DualPlayer** to zaawansowane, przeglądarkowe narzędzie QA (Quality Assurance) przeznaczone do precyzyjnej analizy i porównywania plików wideo. System wspiera pracę inżynierów wideo, pozwalając na jednoczesne odtwarzanie dwóch strumieni (np. wersji emisyjnej i wzorca), automatyczne wykrywanie różnic obrazu, ekstrakcję tekstu oraz generowanie kompleksowych raportów PDF.


### Skróty Klawiszowe (Keyboard Shortcuts)
Dla szybszej nawigacji, aplikacja wspiera podstawowe sterowanie z klawiatury:
- `Spacja (Space)` – Odtwarzanie / Pauza (Play / Pause).
- `Strzałka w prawo (Right Arrow)` – Skok do przodu o jedną klatkę.
- `Strzałka w lewo (Left Arrow)` – Skok do tyłu o jedną klatkę.

*(Uwaga: skróty są automatycznie dezaktywowane, gdy wpisujesz tekst w pole komentarza, aby nie przeszkadzać w pisaniu).*

---

---

## 2. Dokumentacja Techniczna (Architektura)

### Stack Technologiczny
- **Frontend:** React (TypeScript), Tailwind CSS do stylowania.
- **Backend:** Python (FastAPI / Uvicorn), FFmpeg do transkodowania formatów natywnych.
- **Przetwarzanie Obrazu:** HTML5 `<canvas>`, `CanvasRenderingContext2D.getImageData`.
- **Wielowątkowość:** Web Workers API (generowane w locie przez z Blob).
- **Zewnętrzne Biblioteki (Frontend):**
  - `tesseract.js` (OCR - ekstrakcja tekstu)
  - `diff` (porównywanie stringów dla wyników OCR)
  - `jspdf` i `html2canvas` (tworzenie raportów PDF)

### Główne Moduły i Mechanizmy

#### A. Odtwarzanie i Synchronizacja
Aplikacja utrzymuje stałą synchronizację dwóch instancji `HTMLVideoElement` poprzez wspólne metody sterujące (np. `handleSeek`, `handleStep`). Interfejs zapobiega desynchronizacji poprzez wymuszanie jednoczesnego wstrzymywania i odtwarzania obu strumieni.

#### B. Asynchroniczne Web Workery
Aby zapobiec blokowaniu głównego wątku UI, intensywne obliczenia matematyczne na macierzach pikseli (`ImageData`) zostały oddelegowane do Web Workerów:
- **`diffWorker`:** Działa w trybie Dual. Pobiera zrzuty klatek z obu odtwarzaczy i wykonuje porównanie piksel-do-piksela (spatial diff). Zwraca tablicę nakładki (overlay) podświetlającą różnice.
- **`qaWorker`:** Działa w trybie Single. Przetwarza bieżącą i poprzednią klatkę z tego samego wideo (temporal diff). Oblicza średnią luminancję oraz średnią deltę kolorów. Zwraca flagi logiczne: `isBlack`, `isFreeze`, `isSkip`.

#### C. Backend i Transkodowanie (MXF / MOV)
Aplikacja w przeglądarce natywnie wspiera pliki MP4/WebM z pamięci lokalnej (`URL.createObjectURL`). W przypadku plików zaawansowanych (np. profesjonalne formaty MXF, kodeki ProRes w MOV), plik jest asynchronicznie przesyłany przez endpoint API (`/api/v1/files/upload`). Backend wykorzystuje proces FFmpeg do "locie" wygenerowania strumienia przyswajalnego przez przeglądarkę, a frontend odpytuje (polling) o status konwersji i pasek postępu.

---

## 3. Instrukcja Obsługi dla Użytkownika Końcowego (User Manual)

Aplikacja posiada interfejs w języku angielskim, a nawigacja opiera się na dwóch głównych trybach pracy.

### Tryb Dual (Dual Mode) - Porównanie Dwóch Wideo
Tryb domyślny, służący do odtwarzania wideo referencyjnego (Acceptance) i testowego (Emission) obok siebie.
1. **Wczytywanie wideo:** Przeciągnij i upuść plik referencyjny na panel lewy ("Acceptance") oraz plik testowy na panel prawy ("Emission"). 
2. **Sterowanie:** Oś czasu na dole ekranu kontroluje oba wideo jednocześnie. Możesz nawigować po klatkach używając przycisków `<` i `>` (skok o klatkę dla 25 fps).
3. **Narzędzie "Diff ON" (Porównanie wizualne):**
   - Po załadowaniu obu plików kliknij przycisk `Diff ON`.
   - Na wideo nałoży się warstwa podświetlająca drobne (kolor żółty) i krytyczne (kolor czerwony) różnice w klatkach.
   - Poniżej pojawi się sekcja **Wykryte różnice**. Klikając w kafelki na wygenerowanej osi, przeniesiesz się dokładnie do momentu rozbieżności obrazu.

### Tryb Single (Single Mode) - Głęboka Inspekcja
Służy do technicznego sprawdzania pojedynczego pliku wideo. Do tego trybu wejdziesz klikając przycisk "Dual Mode" (zmieni się na "Single Mode").
1. **QA Analysis (Narzędzie Techniczne):**
   - W trybie Single pojawia się przycisk `QA Analysis`.
   - Zaznacz go podczas odtwarzania wideo. Aplikacja przeanalizuje strumień i stworzy oś defektów:
     - ⬛️ **Blackness:** Rozpoznaje czarne klatki lub sekwencje wygaszenia.
     - ❄️ **Freeze:** Rozpoznaje zamrożenie obrazu (np. błąd enkodowania zawieszający klatkę na 2 sekundy).
     - ⚠️ **Frame Skip:** Wskazuje nienaturalne skoki między klatkami wynikające ze zgubionych klatek w samym pliku wideo.

### Narzędzia Dodatkowe (Dostępne na głównym pasku narzędzi)

- 📷 **Screenshot (Zrzut ekranu):**
  Zapisuje obecną klatkę (lub klatki obu wideo) bezpośrednio na Twój dysk komputera.

- 📄 **Raport PDF (Report Builder):**
  Przycisk `Report` otwiera kreator raportu QA. Jeśli znalazłeś błąd, możesz w dowolnej chwili kliknąć `Save to report`. Wpisz swój komentarz do danej klatki. Na koniec pracy możesz wyeksportować wszystkie zrzuty ekranu ze swoimi uwagami do profesjonalnego pliku PDF poprzez przycisk `Generate PDF Report`.

- 👁️‍🗨️ **Odczyt Tekstu (OCR):**
  Pozwala na zaznaczenie dowolnego obszaru na wideo (np. napisów końcowych lub belek). Aplikacja wczyta tekst z obrazu i wyświetli go w panelu poniżej. W trybie Dual aplikacja automatycznie przeprowadzi proces porównywania tekstu z obu plików wideo i zaznaczy brakujące lub błędne słowa!
  *(Uwaga: w opcjach OCR możesz odwrócić kolory dla lepszego sczytywania ciemnych plansz lub określić język dokumentu).*

- 📏 **Miarka (Ruler):**
  Pozwala na narysowanie linii na wideo. Przydatne do badania ułożenia elementów (Safe Area) i proporcji.

- 💉 **Kroplomierz (Eyedropper):**
  Narzędzie umożliwiające najechanie na dowolny punkt w wideo, w celu precyzyjnego zbadania kodu koloru piksela w formacie HEX i RGB. Idealne do inspekcji zachowania brandingu.



# Sync DualPlayer - Technical Documentation and User Manual

## 1. Introduction
**Sync DualPlayer** is an advanced, browser-based QA (Quality Assurance) tool designed for precise video analysis and comparison. The system supports video engineers by allowing simultaneous playback of two streams (e.g., emission version and reference), automatic detection of visual differences, text extraction, and comprehensive PDF report generation.

---

## 2. Technical Documentation (Architecture)

### Technology Stack
- **Frontend:** React (TypeScript), Tailwind CSS for styling.
- **Backend:** Python (FastAPI / Uvicorn), FFmpeg for transcoding native formats.
- **Image Processing:** HTML5 `<canvas>`, `CanvasRenderingContext2D.getImageData`.
- **Multithreading:** Web Workers API (generated on the fly via Blob).
- **External Libraries (Frontend):**
  - `tesseract.js` (OCR - text extraction)
  - `diff` (string comparison for OCR results)
  - `jspdf` and `html2canvas` (PDF report generation)

### Core Modules and Mechanisms

#### A. Playback and Synchronization
The application maintains constant synchronization between two `HTMLVideoElement` instances via shared control methods (e.g., `handleSeek`, `handleStep`). The interface prevents desynchronization by forcing both streams to pause and play simultaneously.

#### B. Asynchronous Web Workers
To prevent blocking the main UI thread, computationally intensive matrix operations on pixels (`ImageData`) are delegated to Web Workers:
- **`diffWorker`:** Active in Dual Mode. Extracts frames from both players and performs pixel-by-pixel spatial comparison. Returns an overlay array highlighting differences.
- **`qaWorker`:** Active in Single Mode. Processes current and previous frames of the same video (temporal diff). Calculates average luminance and average color delta. Returns boolean flags: `isBlack`, `isFreeze`, `isSkip`.

#### C. Backend and Transcoding (MXF / MOV)
The browser app natively supports MP4/WebM files directly from local memory (`URL.createObjectURL`). For advanced files (e.g., professional MXF formats, ProRes codecs in MOV), the file is asynchronously uploaded via an API endpoint (`/api/v1/files/upload`). The backend utilizes FFmpeg to transcode the stream on the fly into a browser-friendly format, while the frontend polls for conversion status and progress.

---

## 3. End User Manual

The application features an English interface and navigation is based on two main working modes.

### Keyboard Shortcuts
For faster navigation, the application supports basic keyboard controls:
- `Space` – Play / Pause.
- `Right Arrow` – Step forward by one frame.
- `Left Arrow` – Step backward by one frame.

*(Note: shortcuts are automatically disabled when typing in a comment field to prevent interference).*

### Dual Mode - Video Comparison
The default mode used to play the reference video (Acceptance) and the test video (Emission) side-by-side.
1. **Loading videos:** Drag and drop the reference file onto the left panel ("Acceptance") and the test file onto the right panel ("Emission").
2. **Controls:** The timeline at the bottom controls both videos simultaneously. You can navigate frame-by-frame using the `<` and `>` buttons (or arrow keys).
3. **"Diff ON" Tool (Visual Comparison):**
   - After loading both files, click the `Diff ON` button.
   - A highlight layer will appear over the video, marking minor (yellow) and critical (red) frame differences.
   - A **Detected Differences** section will appear below. Clicking the tiles on the generated timeline will jump exactly to the moment of discrepancy.

### Single Mode - Deep Inspection
Used for technical inspection of a single video file. Enter this mode by clicking the "Dual Mode" button (it will change to "Single Mode").
1. **QA Analysis (Technical Tool):**
   - In Single mode, the `QA Analysis` button becomes available.
   - Enable it during video playback. The app will analyze the stream and create a defect timeline:
     - ⬛️ **Blackness:** Detects black frames or fade-out sequences.
     - ❄️ **Freeze:** Detects frozen images (e.g., encoding error freezing a frame for 2 seconds).
     - ⚠️ **Frame Skip:** Indicates unnatural frame jumps resulting from dropped frames within the video file itself.

### Additional Tools (Available on the main toolbar)

- 📷 **Screenshot:**
  Saves the current frame (or both frames in Dual mode) directly to your computer's disk.

- 📄 **PDF Report (Report Builder):**
  The `Report` button opens the QA report creator. Whenever you find an error, click `Save to report`. Add your comment to the specific frame. When finished, you can export all screenshots with your notes to a professional PDF file using the `Generate PDF Report` button.

- 👁️‍🗨️ **Text Reading (OCR):**
  Allows you to select any area on the video (e.g., end credits or lower thirds). The application extracts text from the image and displays it in the panel below. In Dual mode, it automatically compares the text from both video files and highlights missing or incorrect words!
  *(Note: in OCR options you can invert colors for better reading of dark backgrounds or specify the document language).*

- 📏 **Ruler:**
  Allows drawing lines on the video. Useful for checking element placement (Safe Area) and proportions.

- 💉 **Eyedropper:**
  A tool that lets you hover over any point in the video to precisely check the pixel's color code in HEX and RGB formats. Perfect for inspecting branding compliance.
