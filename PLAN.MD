# PLAN ZAUTOMATYZOWANEGO QA (PLAYSTATION)

Docelowa wizja to pełna automatyzacja sprawdzania zgodności plików wideo z dostarczonymi wytycznymi i tabelami Excel. Proces wdrażania podzielony został na 3 logiczne etapy.

---
## 🎯 Aktualny Punkt Kontrolny (Zapis Stanu Gry)
**Co ukończyliśmy:** 
Zakończyliśmy przygotowywanie pełnej aplikacji Desktopowej (Standalone `.app` dla systemu macOS spakowanej w `.dmg`). 
Aplikacja ma zintegrowany mechanizm **Auto-Update Checker**, który wymusza na użytkownikach posiadanie najnowszej wersji poprzez sprawdzanie pliku `latest_version.txt` zmagazynowanego na dysku sieciowym VITO (`/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO`). Jeśli lokalna wersja odstaje od najnowszej na serwerze, system używa AppleScript (`System Events`), aby wyświetlić natywne okienko informacyjne macOS i zablokować uruchomienie przestarzałej wersji, co zostało skutecznie przetestowane!

**Co robimy dalej (Czekamy na zielone światło od testera):**
Kolejnym dużym wyzwaniem będzie rozpoczęcie prac nad zarządzaniem bazą danych zasobów do Computer Vision (zgodnie z Etapem 1) lub bazą danych do składowania raportów (Etap 3). Oczekujemy na szczegóły z zespołu QA, by zaplanować właściwą architekturę.
---

## Etap 1: Detekcja Stałych Elementów Graficznych (Obecnie realizowany)
Celem jest potwierdzenie, czy plik posiada odpowiednie elementy stałe wymagane dla danego regionu.
- [ ] Zbudowanie parsera nazw plików (wyciąganie `Language Code`, `Dimension`, `Duration`).
- [ ] Zbudowanie struktury bazy szablonów na backendzie (`bings`, `bongs`, `ratings`).
- [ ] Utworzenie endpointu Computer Vision (FastAPI + OpenCV) przyjmującego klatki i szukającego w nich wzorców (Template Matching).
- [ ] Wdrożenie UI w aplikacji: przycisk "PS Auto-Check", który wyświetla wymagane elementy (na podstawie nazwy pliku) i weryfikuje ich obecność w czasie.

## Etap 2: Integracja z Briefami i Copydeckiem (W przyszłości)
Gdy silnik rozpozna już stałe grafiki, nauczymy go weryfikować zmienne teksty na podstawie plików Excel.
- [ ] Dodanie mechanizmu uploadu plików Excel (Brief/Copydeck) do backendu.
- [ ] Parser plików `.xlsx` w Pythonie (np. biblioteka `pandas` lub `openpyxl`), wyciągający teksty po nagłówkach kolumn dla danego języka (np. `Polish`, `French`).
- [ ] Połączenie mechanizmu OCR (który już mamy we frontendzie) z parserem Excela.
- [ ] Automatyczne porównywanie sczytanego tekstu z wideo z wymaganym tekstem z komórki Excela. Aplikacja upewni się, czy np. pod "AVAILABLE APRIL 30" widnieje na planszy dokładnie tekst "28 KWIETNIA 2026" dla wersji polskiej.

## Etap 3: Raportowanie i Zaawansowane Reguły (W przyszłości)
Ostatni etap to połączenie wszystkiego w kompletny potok audytowy.
- [ ] Rozszerzenie weryfikacji o czas trwania elementu (np. "Bing musi trwać równo 2 sekundy", "Rating musi być widoczny przez pierwsze 5 sekund").
- [ ] Pełna, automatyczna generacja raportu PDF natychmiast po wrzuceniu wideo i kliknięciu "Audyt". Raport będzie zawierał screeny z udokumentowanymi brakami (np. błędna data premiery, brak odpowiedniej ikony PEGI).
- [ ] Możliwość wgrania "Złotego standardu" (Master Video) do automatycznego mapowania layoutu tekstów.
