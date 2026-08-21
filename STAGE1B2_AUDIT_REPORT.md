# Raport z Audytu Obsługi Błędów i Cichych Awarji (STAGE 1B.2)

Zgodnie z poleceniem przeprowadzono pełny i nieinwazyjny audyt plików `backend/main.py` oraz `backend/parsers.py`. Poniżej znajduje się lista znalezisk kategoryzująca sposób, w jaki system reaguje na wyjątki oraz ryzyka załamań dla klienta, uszeregowana ze zwróceniem specjalnej uwagi na priorytetowe błędy "Ciche" (SILENT) oraz "Nieobsłużone" (UNHANDLED).

---

## 🚨 PRIORYTETOWE (Ciche awarie oraz nieobsłużone krasze)

### 🔴 Kategoria A: "SILENT FAILURE" (Błędy ukrywane / zamilczane)
W tych miejscach system całkowicie gubi cenną informację o problemie, okłamując frontend lub zwracając niepełne dane bez informowania użytkownika o podłożu usterki.

1. **`main.py` (L:245, L:252) — Funkcja: `delete_file`**
   - **Opis:** Funkcja łapie wyjątek podczas fizycznego usuwania pliku wideo w `os.remove()`, następnie wykonuje jedynie `print(e)` do logu serwera i powraca do klienta wesoło twierdząc: `{"status": "ok", "detail": "Files deleted successfully"}`. Klient jest przekonany, że plik został usunięty.
2. **`main.py` (L:470, L:476) — Funkcja: `clear_qa_assets`**
   - **Opis:** Analogiczna sytuacja z `os.remove()`. Błąd usuwania briefu/copydecka ukrywa się w `print`, po czym API zawsze gwarantuje `{"success": True}`. 
3. **`parsers.py` (L:28, L:46, L:69, L:97) — Funkcja: `extract_rating_icon_from_brief`**
   - **Opis:** Funkcja parsowania wewnętrznych rysunków z Excela wyłapuje kluczowe potknięcia bibliotek (`openpyxl`, błędy wewnętrzne `zipfile` i `KeyError`) – zamiast informować, że "szablon w briefie jest uszkodzony", po prostu zwraca `None`. Na frontend API przekazuje wtedy po prostu `null` pod spodem.
4. **`main.py` (L:284) — Funkcja: `get_cached_image`**
   - **Opis:** Awaria silnika OpenCV przy czytaniu z cache jest logowana tylko wewnętrznym printem i ucinana w zwracanym `None`.
5. **`main.py` (L:487) — Funkcja: `get_base64_from_path`**
   - **Opis:** Niemożliwość wczytania zasobu z dysku i zdekodowania na Base64 ukrywa problem zwracając `None`.
6. **`main.py` (L:573) — Funkcja: `match_brief_icon_to_db`**
   - **Opis:** Ciche łapanie globalnego wyjątku dla błędów alokacji algorytmu ORB lub błędów OpenCV, dające na zewnątrz czyste `None, 0`.
7. **`main.py` (L:842, L:875, L:884, L:944, L:969) — Funkcja: `analyze_elements`**
   - **Opis:** Liczne ciche bloki rzucające `pass` lub podstawiające stałą wartość.

### 🔴 Kategoria D: "UNHANDLED" (Ryzyko twardego przerwania)
Ryzykowne wywołania wyłamujące się z kontroli potokowej bez try/catch, które w wypadku awarii uwalą sam proces lub doprowadzą klienta do zawieszenia pętli (np. "nieskończony loading").

1. **`main.py` (L:182) — Wewnątrz: `upload_file` (w funkcji pobocznej wątku)`**
   - **Opis:** Wywołanie zapisu (`open()` i `shutil.copyfileobj()`) delegowane do tła bez jakiegokolwiek `try...except`. Jeżeli dysk się zapełni lub padną uprawnienia – wątek wybuchnie kompletnie zrzucając odpowiedź. Baza danych zachowa dla pliku status wgrany (ale nieskończony proces transkodowania – brak przejścia z `is_processed: False`), a klient na zawsze utknie w UI.
2. **`main.py` (L:1030, L:1053, L:402) — Wewnątrz: `analyze_elements`, `upload_brief`**
   - **Opis (Bomba w obsłudze wyjątków!):** Logika tworzenia i pisania do `/tmp/vito_error.log` lub zapisywania zrzutów ramek do debuggera została umieszczona... wewnątrz samych bloków obsługi `except` lub `try`. Gdy to otwarcie pęknie (np. brak przestrzeni na `/tmp` lub uprawnień roota w kontenerze) – aplikacja wysadzi w kosmos oryginalny wyjątek wprowadzając twardy crash!
3. **`main.py` (L:650) — Funkcja: `analyze_elements`**
   - **Opis:** Kod `cv2.imdecode(nparr)` może (i przy uszkodzeniach zwraca) `None`. Nie ma w tym miejscu zabezpieczenia - dalsze kroki takie jak `img_np.shape` momentalnie wyrzucą nieprzechwycony `AttributeError`, powodując wysyp 500 w głównym wątku.

---

## 🟡 ZWYKŁE OBSŁUGI BŁĘDÓW 

### 🟠 Kategoria B: "GENERIC 500" (Propagacja suchego błędu)
W poniższych wypadkach klient dowiaduje się, że wystąpił błąd, ale jest on brzydkim, maszynowym surowcem bibliotek bez oprawy deweloperskiej.

1. **`main.py` (L:456) — Funkcja: `upload_brief`**
   - **Opis:** Końcówka `except Exception as e:` podnosi HTTPException o statusie 500 przeklejające po prostu `str(e)`. Użytkownik widzi generyczne błędy pakietu np. Pandasa.
2. **`main.py` (L:1050) — Funkcja: `analyze_elements`**
   - **Opis:** Ogólne opakowanie serca analizy, gdzie na zewnątrz leci wielki słownik JSON, lecz pole `error` zawiera suchy `str(e)`.

### 🟢 Kategoria C: "PROPER HANDLING" (Poprawna logika)
Punkty, które dbają o jakość API i dają jasne powody porażki klientom/biznesowi.

1. **`parsers.py` (L:110, 116, 178, 181)**
   - **Opis:** Rzucanie świetnie sformułowanych, biznesowych wiadomości `ParserError` z precyzyjnym wskazaniem dlaczego coś zawiodło (np. "Brak kodu języka w nazwie").
2. **`main.py` (L:657, L:683) — Wewnątrz `analyze_elements`**
   - **Opis:** Przechwytywanie błędów z parsers.py w try/catch i rzucanie kulturalnego błędu `400` do klienta na HTTP.
3. **`main.py` (L:156, L:160) — `transcode_to_mp4` (FFmpeg)**
   - **Opis:** Odpowiedź na zadane w konwersacji pytanie: Jeżeli wywołanie `subprocess.Popen` dla FFmpeg padnie (`returncode != 0`), skrypt nie wyrzuca błędów cicho na podłogę. Zapamiętuje awarię jako flaga `files_db[file_id]["processing_error"] = "FFmpeg failed to transcode"`. Klient uderzając w `/api/v1/files/{file_id}` otrzymuje tę flagę (choć bez precyzyjnego STDERR by wiedzieć *dlaczego* transkodowanie padło, ale sama obsługa jest prawidłowa). Zatem FFmpeg NIE posiada wariantu D ani czystego A.
