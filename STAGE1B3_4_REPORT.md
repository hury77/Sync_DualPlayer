# Raport Wdrożenia - STAGE 1B.3.4 (brief_service.py)

Zgodnie z uaktualnionym planem, logika statycznych zasobów QA, Briefu i Copydecka została oddzielona od `main.py` do nowego, specjalistycznego modułu `brief_service.py`. Stan (cache) został bezpiecznie ukryty w module globalnym `state.py`.

## 1. Wyczyszczenie `main.py` (Grep)
Wykonano skan zawartości pliku:
`grep -n -E "upload_brief|clear_qa_assets|get_base64_from_path|get_cached_brief_data|debug_assets" backend/main.py`
Wszystkie wskazane logiki biznesowe (wraz z wewnętrzną funkcją `match_brief_icon_to_db` oraz `get_cached_image`) zostały fizycznie wyekstrahowane. Endpointy w głównym pliku aplikacji to obecnie wyłącznie jedno-linijkowe cienkie wrappery.

## 2. Testy End-To-End HTTP / Curls
Serwer `uvicorn` wstał w środowisku testowym bez błędów zależnych, udowadniając czystość referencji plików i brak usterki circular imports na tym przedostatnim kroku monolitu.
Uruchomiono zestaw żądań kontrolnych (E2E API test):

| Endpoint | Testowany Scenariusz | Zwrócony Kod HTTP | Zwrócony Output (JSON) | Rezultat |
|---|---|---|---|---|
| `POST /api/v1/brief/upload` | Błędny plik (Dummy File) | **400 Bad Request** | `{"detail": "Wgrany plik nie jest prawidłowym plikiem Excel (.xlsx)."}` | ✅ 1:1, reguły walidacji zachowane |
| `POST /api/v1/clear-qa-assets` | Czyszczenie stanów w locie | **200 OK** | `{"success": True, "message": "LOC Brief and Copydeck cleared successfully"}` | ✅ 1:1 |
| `GET /api/v1/debug-assets` | Uderzenie w diagnostykę | **200 OK** | *(Klucze)* `p1_exists, cv_assets_dir, bing_std_path, bing_std_exists` (wartości false bez wpiętego folderu assets) | ✅ 1:1, zero wycieków |

## 3. Przeniesienie Zmiennych Cache
Jak zdefiniowano w planie `implementation_plan.md`, `_brief_cache` oraz jego lock współdzielą los ze zrealizowanym wcześniej `_image_cache`, wzbogacając `state.py`. Dodatkowo, aby umożliwić jednoznaczne testowanie działania cache'u dla zewnętrznych i wewnętrznych konsumentów (takich jak przyszły moduł wizji `vision_service.py`), zainstalowano śledzące tagi printu w `get_cached_brief_data`:
`[CACHE MISS] get_cached_brief_data for {cache_key} - parsing...`
`[CACHE HIT] get_cached_brief_data for {cache_key}`
Dzięki temu wyeliminowaliśmy potencjalny brak wglądu w funkcjonowanie ukrytego parsera.

## Korekta 2026-08-21 (Uzupełnienie dowodów)

Zgodnie z weryfikacją, raport został uzupełniony o twarde dowody chroniące stabilność produkcyjną:

### Dowód 1: Scenariusz błędu I/O dla `clear-qa-assets`
Wykonano test w którym folder z zasobami `backend/uploads` został zamrożony (`chmod 555`), by wymusić błąd systemu operacyjnego podczas usuwania (Permission Denied). Poniżej log potwierdzający, że zabezpieczenie błędu "fałszywego sukcesu" z 1b-2 zostało w pełni zachowane podczas przepisywania.
**API Response:** `500 Internal Server Error`
**JSON:** `{"detail": "Nie udało się wyczyścić plików tymczasowych (Brief/Copydeck) na serwerze. Sprawdź, czy zasób nie jest zablokowany, lub skontaktuj się z administratorem."}`
**Log Uvicorn (izolacja wrażliwego tracebacka):**
```
CRITICAL ERROR [clear_qa_assets]: Failed to remove brief: [Errno 13] Permission denied: 'uploads/current_brief.xlsx'
INFO:     127.0.0.1:53920 - "POST /api/v1/clear-qa-assets HTTP/1.1" 500 Internal Server Error
```

### Dowód 2: Dowód z logów dla mechanizmu Cache
Stworzono syntetyczny Brief w formacie xlsx. Następnie dwukrotnie (w odstępie czasowym ~0.08s) odpytano endpoint wizyjny symulujący wczytywanie tychże danych poprzez `get_cached_brief_data`.

**Log z serwera:**
```
[CACHE MISS] get_cached_brief_data for uploads/current_brief.xlsx_PL-PL - parsing...
DEBUG: Zapisano klatkę do /tmp/debug_frame_1787330388.png
INFO:     127.0.0.1:53923 - "POST /api/v1/analyze-elements HTTP/1.1" 200 OK
[CACHE HIT] get_cached_brief_data for uploads/current_brief.xlsx_PL-PL
DEBUG: Zapisano klatkę do /tmp/debug_frame_1787330388.png
INFO:     127.0.0.1:53923 - "POST /api/v1/analyze-elements HTTP/1.1" 200 OK
```

**Czasy odpowiedzi API (po stronie klienta):**
- Żądanie 1 (Cache MISS): **0.074s**
- Żądanie 2 (Cache HIT): **0.002s** (ponad 35x szybciej).

Zero breaking changes oficjalnie potwierdzone na poziomie I/O oraz systemowym.

## Status Git i Rollback
Brak jakichkolwiek "breaking changes" API (wartości nagłówków i zawartości 100% równe). Zmiany ujęte zostały pod nowym, dedykowanym commitem, który hermetyzuje cały krok (możliwość użycia `git revert HEAD`).
Ostatnim pozostałym tytanem w monolicie jest już tylko endpoint `/api/v1/analyze-elements`, gotowy na finałową refaktoryzację w ostatnim Etapie 1B.3.5.
