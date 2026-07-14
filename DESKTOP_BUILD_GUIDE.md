# Architektura Standalone (Lokalna Aplikacja Desktopowa macOS) oraz Procedura QA

Ten dokument opisuje architekturę i procedurę budowania lokalnej, samodzielnej aplikacji desktopowej macOS (`.app` / `.dmg`) oraz listę kontrolną weryfikacji przed udostępnieniem jej zespołowi.

---

## 1. Główne Założenia i Architektura

Aplikacja standalone składa się z czterech zintegrowanych warstw:
1. **Skompilowany Frontend (React):** Statyczny build (HTML, JS, CSS) serwowany bezpośrednio przez backend.
2. **Lekki Backend (FastAPI):** Pythonowy serwer uvicorn działający lokalnie na porcie `8080`, obsługujący API i serwowanie plików frontendu.
3. **Natywny Wrapper Binarny (C / Mach-O Universal Binary):** 
   Natywna, skompilowana w C aplikacja konsolidująca, stanowiąca główny punkt wejściowy (`CFBundleExecutable`). Wspiera architektury Apple Silicon (`arm64`) oraz Intel (`x86_64`).
4. **Metadane Uprawnień (`Info.plist`):** 
   Konfiguracja TCC (Transparency, Consent, and Control) określająca cel dostępu do plików systemowych i sieciowych.

```
Sync_DualPlayer.app/
└── Contents/
    ├── Info.plist               <-- Deklaracje uprawnień TCC (Dysk Sieciowy/Dokumenty)
    ├── Resources/
    │   └── icon.icns            <-- Ikona wyświetlana w Docku oraz Finderze
    └── MacOS/
        ├── Sync_DualPlayer      <-- Skompilowany wrapper binarny w C (Mach-O)
        ├── Sync_DualPlayer_run.sh <-- Główny skrypt bash (konfiguruje venv, odpala uvicorn)
        └── src/                 <-- Pliki źródłowe backendu i frontendu
```

---

## 2. Rozwiązanie Problemu Uprawnień macOS (TCC & Sandboxing)

Głównym problemem środowisk opartych wyłącznie na skryptach shellowych wewnątrz paczek `.app` uruchamianych z poziomu Findera jest **ciche blokowanie dostępu do zasobów zewnętrznych** (np. `/Volumes/PL-EGplusww/`). macOS ze względów bezpieczeństwa nie wyświetla dla skryptów bashowych okien zapytania o uprawnienia i blokuje ich operacje dyskowe.

### Rozwiązanie:
* **Kompilacja C:** Główny plik `Sync_DualPlayer` jest skompilowanym plikiem binarnym w języku C. Uruchamia on skrypt bashowy za pomocą funkcji systemowej `execl`:
  ```c
  execl("/bin/bash", "bash", script_path, (char *)NULL);
  ```
  macOS traktuje to jako natywny proces GUI i pozwala na poprawne zarządzanie uprawnieniami.
* **Deklaracje w Info.plist:** W pliku `Info.plist` zadeklarowano klucze:
  ```xml
  <key>NSNetworkVolumesUsageDescription</key>
  <string>Aplikacja wymaga dostępu do dysku sieciowego w celu wczytania szablonów CV_Assets.</string>
  <key>NSDocumentsFolderUsageDescription</key>
  <string>Aplikacja wymaga dostępu do folderu Dokumenty w celu wczytania szablonów CV_Assets.</string>
  ```
  Dzięki temu system pyta użytkownika o dostęp (jednorazowo), po czym zapisuje zgodę w preferencjach systemowych. Aplikacja działa bez terminala na pierwszym planie, prezentując dedykowaną ikonę w Docku.

---

## 3. Kompilacja i Pakowanie (`build_dmg.sh`)

Budowanie całej aplikacji odbywa się za pomocą jednego polecenia:
```bash
./build_dmg.sh
```

**Kroki wykonywane automatycznie przez skrypt:**
1. Kompilacja kodu frontendu (React/Vite).
2. Kopiowanie wygenerowanych plików statycznych do katalogu `.app`.
3. Kopiowanie skryptów backendu oraz zainicjowanie plików wersji.
4. Kompilacja binarnego wrappera wejściowego (`wrapper.c`) jako **Universal Binary** (dla arm64 oraz x86_64).
5. Nadanie uprawnień wykonywania (`chmod +x`).
6. Wygenerowanie spakowanego obrazu dystrybucyjnego `.dmg`.

---

## 4. Procedura QA przed Udostępnieniem Zespołowi (Checklista)

Przed każdym wydaniem nowej wersji aplikacji standalone do zespołu, wykonaj poniższe kroki weryfikacyjne w celu uniknięcia regresji:

### Krok 1: Weryfikacja czystości portu 8080
Przed uruchomieniem upewnij się, że port `8080` nie jest zajęty przez wiszący stary proces:
```bash
lsof -i :8080
```
*Jeśli polecenie coś zwróci, ubij proces (`kill -9 PID`) lub poczekaj, aż skrypt startowy zrobi to automatycznie.*

### Krok 2: Weryfikacja zamontowania dysku sieciowego
Upewnij się, że dysk sieciowy `PL-EGplusww` jest zamontowany w systemie operacyjnym:
```bash
ls -la /Volumes/PL-EGplusww
```
*Dysk musi być zamontowany w Finderze (skrót Cmd+K -> smb://...), a folder szablonów `CV_Assets` musi być widoczny.*

### Krok 3: Test czystego uruchomienia
1. Uruchom nowo skompilowaną aplikację z katalogu aplikacji: `/Users/hubert.rycaj/Applications/Sync_DualPlayer.app`.
2. Upewnij się, że:
   * **NIE** otwiera się puste, czarne okno Terminala.
   * Na pasku Dock pojawia się ikona **Sync DualPlayer** (a nie ikona terminala).
   * Karta w przeglądarce pod adresem `http://localhost:8080` otwiera się automatycznie.

### Krok 4: Weryfikacja uprawnień (TCC)
Przy pierwszym uruchomieniu po instalacji lub zmianie sygnatury upewnij się, że:
1. macOS wyświetlił komunikat pytający o uprawnienia dostępu do dysku sieciowego / wolumenu.
2. Kliknięto **OK**.

### Krok 5: Test integracyjny analizatora (PS Auto-Check)
1. Wgraj plik briefu `.xlsx` oraz dowolny plik wideo QA (np. `MX-ES`).
2. Kliknij przycisk **PS Auto-Check**.
3. Sprawdź, czy statusy dopasowania BING, Rating i BONG zmieniły się na zielone `FOUND` (lub prawidłowo zweryfikowane wartości procentowe).
4. Sprawdź plik logów `/tmp/vito_error.log`, aby upewnić się, że dopasowanie przebiegło poprawnie i uzyskało współczynniki powyżej progu akceptacji (szablony wczytane z sieci):
   ```bash
   tail -n 20 /tmp/vito_error.log
   ```
   *Powinieneś zobaczyć wpisy typu: `[CV DEBUG] match_template: path=/Volumes/PL-EGplusww/... matched=True`.*
