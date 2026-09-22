# STAGE 1E-2 REPORT: Deep Audio Analysis Integration

## 1. Wyodrębnienie Fixu (-inf LUFS/Peak)
Błąd wynikający z całkowicie cichych plików (`-inf` od FFmpeg) psuł parsowanie JSON. 
Poprawka (zamiana nieskończoności na krawędzie -70.0/-99.0) została wydzielona do niezależnego commita ("fix(audio): handle -inf LUFS/peak values..."). Odtworzenie zachowania zostało sformalizowane i zabezpieczone stałym plikiem `silent.wav` dodanym do siatki `test_audio.py`.

## 2. Optymalizacja i Blokada Współbieżności
Z powodu znacznego obciążenia pamięci (Whisper: ~750MB, Demucs: ~1.2GB):
- Zaimplementowano operację GC Cleanup po zakończeniu dekodowania modelu Whisper. Przed załadowaniem Demucs instancja Whisper zostaje zwolniona, co skutecznie minimalizuje Peak RAM.
- Wprowadzono twardą blokadę `asyncio.Lock()` (`_analysis_lock = asyncio.Lock()`) obejmującą cykl transkrypcji i separacji, gwarantującą, że na serwerze dokonywana jest maksymalnie jedna analiza na raz. Zapytania od frontendu są kolejkowane poprzez system asynchroniczny i zwracają poprawne "processing", chroniąc UX aplikacji.

## 3. Bezpieczeństwo Zależności (SSL FIX)
Zlikwidowano luki konfiguracyjne ze środowiska /tmp. Skonfigurowano model Demucs do używania poprawnej listy certyfikatów (`os.environ["SSL_CERT_FILE"] = certifi.where()`) w miejsce niebezpiecznych monkey-patchy httpx i pustych `REQUESTS_CA_BUNDLE`. Osiągnięto czystą od wyłączeń weryfikacji bazę (`verify=False`).

## 4. Separacja Demucs (2-Stems)
Potwierdzono, że zastosowana metoda oddzielenia wokali od reszty muzyki poprzez zsumowanie wszystkich innych kanałów w `no_vocals` to jedyne prawidłowe podejście. W bibliotece demucs obydwie metody wczytują pełen 4-ścieżkowy tensor, narzucając przewidywalny bazowy footprint pamięci VRAM/RAM. 

## 5. Czystość Repozytorium i Pliki Testowe
Wszystkie skrypty reconowe (`prove_bug.py`, pliki audio o długości 115s służące wyłącznie do zbadania pamięci peak RAMu) zostały usunięte z drzewa roboczego. Duże pliki badawcze rzędu kilkudziesięciu megabajtów (np. `audio_115s.wav`) zostały skasowane by uniknąć trwałego zapchania historii repozytorium. Śledzeniem objęto jedynie niezbędne, krótko-działające pliki dla pytest (np. `silent.wav`).

*Raport jest ostatecznym, zatwierdzonym podsumowaniem STAGE 1E-2.*
