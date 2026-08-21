# Raport z audytu repozytorium (Stage 0 Recon)

## 1. Drzewo katalogów z opisem
Główne pliki i ich rola w repozytorium:
- `/backend/generate_mocks.py`: Skrypt generujący testowe (zaślepione) pliki i makiety na potrzeby mockowania.
- `/backend/main.py`: Główny plik aplikacji FastAPI, odpowiada za wystawianie API, przetwarzanie wideo oraz implementację logiki rozpoznawania obrazu (Computer Vision).
- `/backend/parsers.py`: Zestaw funkcji dekodujących nazwy plików wideo oraz wyciągających dane ze specyficznych struktur plików XML/Excel (Brief, Copydeck).
- `/build_dmg.sh`: Skrypt powłoki zajmujący się zbudowaniem natywnej aplikacji i stworzeniem pakietu DMG dla macOS.
- `/create_mock_excel.py`: Narzędzie pomocnicze do tworzenia fikcyjnych plików Excel (XLSX) dla testowania parserów z backendu.
- `/fix_button.js`: Jednorazowy, niezintegrowany z buildem plik naprawiający specyficzny błąd DOM na stronie.
- `/frontend/src/App.tsx`: Główny korzeń komponentów Reacta, spinający ramy interfejsu aplikacji.
- `/frontend/src/components/SyncDualPlayer.tsx`: Rdzeń aplikacji frontendowej; potężny komponent integrujący odtwarzacz wideo, komunikację z API i logikę prezentacji.
- `/frontend/src/main.tsx`: Punkt wejścia (entrypoint) Vite do inicjalizacji DOM z aplikacją React.
- `/frontend/src/utils/Roboto-Regular.ts`: Osadzona bezpośrednio w kodzie (ciąg base64) czcionka Roboto używana do dynamicznego generowania raportów PDF.
- `/frontend/src/workers/diffWorker.ts`: Asynchroniczny Web Worker wyliczający różnice (diff) w dużych tekstach w tle, aby nie spowalniać głównego wątku UI.
- `/frontend/test-jspdf.cjs`: Lokalny skrypt testujący generowanie plików PDF biblioteką `jspdf`.
- `/frontend/vite.config.ts`: Konfiguracja bundlera Vite, zajmująca się definicjami portów, wtyczkami Reacta oraz procesem build/dev.
- `/scratch/*.py`: Bardzo rozbudowany katalog skryptów jednorazowych (np. `apply_layout.py`, `test_bong.py`, `crop_test.py`), stanowiący swoisty "brudnopis" deweloperski logiki przetwarzania obrazu. Żaden plik nie jest częścią produkcyjnej struktury.
- `/scratch/run_and_test.sh`: Prosty skrypt pomocniczy bash ułatwiający seryjne odpalanie wyselekcjonowanych skryptów eksperymentalnych.
- `/start.sh`: Shellowy orchestrator do jednoczesnego uruchamiania serwera uvicorn (backend) oraz Vite (frontend).
- `/test_api.py`: Zewnętrzny skrypt ad-hoc używany do ręcznego rzucania zapytań HTTP pod endpoint `/api/v1/analyze-elements`.
- `/translate_ui.py`: Niezależny skrypt narzędziowy do prac przy UI (prawdopodobnie do generowania/migracji tłumaczeń).
- `/wrapper.m`: Natywny kod w Objective-C służący do osadzenia strony w natywnym oknie (WKWebView) pod system macOS.

## 2. Zależności zewnętrzne
### Backend (z requirements.txt)
- `fastapi`: Framework webowy używany bezpośrednio do deklaracji i wystawiania tras/endpointów API.
- `uvicorn`: Serwer aplikacji ASGI serwujący i utrzymujący uruchomioną aplikację FastAPI zdefiniowaną w main.py.
- `python-multipart`: Rozszerzenie dla FastAPI umożliwiające natywną konsumpcję i obsługę przesyłania plików z formularzy (UploadFile).
- `imageio-ffmpeg`: Wykorzystywana do pozyskiwania ścieżki i dostarczenia binarki programu `ffmpeg` używanego do konwersji formatów wideo na H.264.
- `opencv-python` (`cv2`): Zaawansowane manipulacje klatkami obrazu – używana na potęgę do Computer Vision, progowania i template matchingu (`cv2.matchTemplate`, `cv2.ORB_create`).
- `numpy`: Wykorzystywana do operacji numerycznych i przekształceń wielowymiarowych matryc (ndarray) pochodzących ze zdekodowanych obrazów.
- `pandas`: Służy jako interfejs analityczny wczytujący arkusze kalkulacyjne z wymogami projektu prosto do struktur DataFrame.
- `openpyxl`: Działający w tle silnik używany przez Pandas oraz parsery XML/ZIP do dekonstrukcji plików Excel (.xlsx).

### Frontend (z package.json)
- `react`, `react-dom`: Biblioteka widoków implementująca wirtualny DOM, wokół której zbudowany jest cały interfejs webowy.
- `vite`, `@vitejs/plugin-react`: Superszybki serwer deweloperski i budowniczy kodu źródłowego dla końcowej aplikacji.
- `tailwindcss`, `@tailwindcss/vite`, `postcss`, `autoprefixer`: Silnik układu stylów i biblioteka utility-first, za pomocą której zdefiniowano całe ostylowanie UI.
- `@heroicons/react`: Biblioteka użyta do osadzania wektorowych ikon (SVG) używanych w przyciskach i interfejsie.
- `diff`: Stosowana we wbudowanym Web Workerze do precyzyjnego wyliczania brakujących lub błędnych fragmentów tekstu między odczytem z OCR a Copydeckiem.
- `tesseract.js`: Implementacja silnika OCR w JS wykonująca w przeglądarce odczyt tekstów z uchwyconej klatki wideo.
- `jspdf`, `html2canvas`: Narzędzia konwertujące ustrukturyzowany HTML do formatu Canvas, a następnie układające te fragmenty w spójny dokument PDF gotowy do pobrania z UI.

## 3. Mapa API
Wszystkie zdefiniowane w backendzie endpointy (z `/backend/main.py`):
1. **POST** `/api/v1/files/upload`
   - *Linia:* 123
   - *Request Model:* Form/File (`file: UploadFile`, `file_type: str`). Brak walidacji Pydantic.
   - *Response Model:* JSON (zwykły słownik).
2. **GET** `/api/v1/files/{file_id}`
   - *Linia:* 160
   - *Request Model:* Parametr URL (`file_id: int`). Brak walidacji Pydantic.
   - *Response Model:* JSON (zwykły słownik).
3. **GET** `/api/v1/files/stream/{file_id}`
   - *Linia:* 175
   - *Request Model:* Parametr URL (`file_id: int`). Brak walidacji Pydantic.
   - *Response Model:* Strumień danych `FileResponse`.
4. **DELETE** `/api/v1/files/{file_id}`
   - *Linia:* 188
   - *Request Model:* Parametr URL (`file_id: int`). Brak walidacji Pydantic.
   - *Response Model:* JSON (zwykły słownik).
5. **POST** `/api/v1/brief/upload`
   - *Linia:* 365
   - *Request Model:* Form/File (`file: UploadFile`). Brak walidacji Pydantic.
   - *Response Model:* JSON (zwykły słownik).
6. **POST** `/api/v1/clear-qa-assets`
   - *Linia:* 409
   - *Request Model:* Brak danych wejściowych. Brak walidacji Pydantic.
   - *Response Model:* JSON (zwykły słownik).
7. **GET** `/api/v1/debug-assets`
   - *Linia:* 560
   - *Request Model:* Brak danych wejściowych. Brak walidacji Pydantic.
   - *Response Model:* JSON (zwykły słownik).
8. **POST** `/api/v1/analyze-elements`
   - *Linia:* 592
   - *Request Model:* `req: AnalyzeFrameRequest`. **Jako jedyny endpoint posiada walidację struktury wejściowej za pomocą Pydantic (BaseModel)**.
   - *Response Model:* JSON (zwykły słownik z analizą).
9. **POST** `/api/v1/copydeck/parse`
   - *Linia:* 1009
   - *Request Model:* Form/File (`file: UploadFile`). Brak walidacji Pydantic.
   - *Response Model:* JSON (zwykły słownik).

## 4. Stan testów
### Katalog i charakterystyka testów
Zidentyfikowane pliki z potencjalnym przeznaczeniem testowym to:
- `test_api.py` 
- `frontend/test-jspdf.cjs`
- Cały ogromny zestaw wewnątrz `scratch/` (np. `test_rating.py`, `test_api_bong.py`, `test_match2.py`, `test_scale.py`, `verify_order.py`, itp.)
- Oraz plik powłoki `scratch/run_and_test.sh` do ręcznego startowania powiązanych weryfikacji.

**Ocena:**
- **Żaden z plików nie jest testem automatycznym** wykorzystującym znormalizowane frameworki testowe (jak Pytest czy Vitest). 
- To wyłącznie jednorazowe, ad-hoc skrypty do iteracyjnego sprawdzania logiki z punktu widzenia developera na lokalnym środowisku. 

### Pokrycie funkcji biznesowych
- Pokrycie strukturalne kodem testów uruchamianych w automatycznym cyklu: **0%**.
- Kluczowe funkcje biznesowe CAŁKOWICIE POZBAWIONE WERYFIKACJI JEDNOSTKOWEJ:
  - Walidacja i transformacja plików Brief (arkusze kalkulacyjne/XML).
  - Skomplikowany proces Computer Vision odpalany w funkcji `match_template`.
  - Transkodowanie plików binarnych FFmpeg (logika wątków z postępem konwersji).
  - Skrypty obsługujące ujednolicone API.

## 5. Podejrzane pliki
W repozytorium zauważono artefakty niedające się logicznie włączyć w ekosystem wykonawczy:
1. `fix_button.js`: Odosobniony skrypt JS. Brak jakichkolwiek śladów importowania lub odwołań na frontendzie i backendzie. Podejrzenie wczorajszego hotfixa zakorzenionego poza systemem kontroli Vite.
2. `create_mock_excel.py`: Skrypt nie odpalany w żadnym miejscu aplikacji poza jednorazowym wytworzeniem bazy (pustych stubów). 
3. `translate_ui.py`: Nieprzypisane nigdzie narzędzie (być może porzucony skrypt translacyjny starych struktur). Brak importów.
4. `frontend/tailwind.config.js.bak`: Zapomniany i bezwartościowy backup poprzedniej konfiguracji układu (przy migracji do v4), który powinien być skasowany a historia śledzona git-em.
5. `Katalog scratch/`: Zbiór niepołączonych w paczkę modułów skryptów weryfikacyjnych i roboczych.
*Uwaga nt. konfiguracji:* Znaleziono wiele plików `tsconfig.*.json` w folderze frontend. NIE SĄ TO DUPLIKATY bezwartościowe. Wynika to ze specyfiki Vite oddzielającej definicje globalne Node (konfiguracja bundlera) od struktur dla środowiska przeglądarki. Mają one pełne zastosowanie.

## 6. Konfiguracja i sekrety
Podczas pełnego prześwietlenia repozytorium **nie wykryto hardcodowanych kluczy uwierzytelniania, tokenów chmurowych ani haseł**. Znaleziono natomiast mocno powiązane z infrastrukturą zjawiska:
- **`backend/main.py` (L:566, L:621)**: Widnieje tam odwołanie zaszyte na twardo w kod: `Path("/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets")`. Jest to wywołanie dysku sieciowego powiązane tylko ze stacją posiadającą lokalny montaż (Luka portabilności na innych OS!).
- **`scratch/test_rating.py` (L:5)**: Ścieżka `/Users/hubert.rycaj/Documents/PS_elements/CV_Assets`, która poświadcza wykorzystywanie roboczych odnośników na osobistej maszynie.
- **`test_api.py` (L:19)**: Statyczne zawołanie do `http://localhost:8003/api/v1/analyze-elements`, co potwierdza użytkowanie w testach roboczego gniazda.
Na frontendzie nie ma wycieku do nieznanych API oprócz komentarza objaśniającego porty w pliku `SyncDualPlayer.tsx` na linii 809.

## 7. main.py - analiza szczegółowa
Pełna lista zdefiniowanych procedur z backendowego modułu `main.py` w kolejności występowania w pliku:
1. `get_robust_ffmpeg_exe`: Szuka i zwraca prawidłową ścieżkę do wykonywalnego pliku binarnego `ffmpeg` (skrypt wspiera załączoną do pakietu, wbudowaną binarkę).
2. `transcode_to_mp4`: Działająca w tle procedura wykonująca rzeczywiste przetworzenie wideo dowolnego formatu (ProRes/MXF/MOV) do formatu odtwarzalnego w webie (H.264 MP4).
3. `upload_file`: Odbiera od klienta surowy plik wideo, rejestruje go w lokalnej bazie operacji i włącza cykl transkodowania.
4. `get_file_status`: Odpowiada na żądanie sprawdzenia stanu aktualnego transkodowania i oddaje procentowy postęp prac nad plikiem.
5. `stream_file`: Endpoint odsyłający żądanie (FileResponse) pliku strumieniowego – umożliwia przewijanie odtwarzanego, przekonwertowanego wideo.
6. `delete_file`: Czyszczący algorytm sprzątający na dysku i w pamięci po odrzuconym/zakończonym projekcie.
7. `AnalyzeFrameRequest`: Definicja modelu wejściowego dla zapytania (zawiera bazę w Base64 oraz detale struktury).
8. `get_cached_image`: Inteligentny ładowacz klatek poprzez OpenCV; przetrzymuje już załadowane obrazki w słowniku by nie wczytywać ciągle szablonów z dysku.
9. `match_template`: Serce analityczne – algorytm wykorzystujący skalowanie, przycinanie i metryki Computer Vision w celu wykrycia na zrzucie elementów (CV_Assets) z określoną czułością.
10. `upload_brief`: Moduł weryfikacji i przechwytu załącznika pliku Excelowego sprawdzający autentyczność zakładek oraz zawartość pod kątem struktury Brief.
11. `clear_qa_assets`: Usuwający stare arkusze Brief oraz powiązany z nim Copydeck moduł przygotowawczy na nowy projekt.
12. `get_base64_from_path`: Trywialny pomocnik czytający plik obrazkowy i generujący ciąg Base64 przygotowany pod standard HTML Image Src.
13. `match_brief_icon_to_db`: Inteligentny moduł analityczny ekstrakcji i przyrównywania – używa algorytmu wyodrębniania cech (ORB) na znalezienie pasującej ikony PEGI/ESRB do szablonu zapisanego na systemie.
14. `get_cached_brief_data`: Odczytuje, dekoduje z pomocą parserów i zrzuca do pamięci procesowej kluczowe, techniczne wymogi (wiek, szablony bong/bing, kraj) z analizowanego arkusza Brief.
15. `debug_assets`: Tryb roboczy diagnostyczny sprawdzający integralność podłączonych nośników montażowych i stanów katalogów CV.
16. `analyze_elements`: Główny silnik logiczny procesu CV - odbiera zdekodowane wymogi i parametry pliku, buduje strukturę katalogową pod wyszukiwane asety i koordynuje poszukiwania na wysłanej klatce algorytmem dopasowania wzorca.
17. `parse_copydeck`: End-point pobierający do parsowania tekst nałożony na grafiki (Copydeck), najprawdopodobniej by zasilić nim proces OCR oraz system pokazywania różnic (diffWorker).
