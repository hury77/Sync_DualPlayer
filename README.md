# Sync DualPlayer

Sync DualPlayer to błyskawiczna, przeglądarkowa aplikacja webowa do perfekcyjnie zsynchronizowanego odtwarzania dwóch plików wideo, wyodrębniona z głównego systemu Cradle Video Automation. Odtwarzacz oferuje tryb rentgena (X-Ray wipe), narzędzia do sprawdzania różnic pikseli, lupy kolorystyczne (eyedropper) oraz linijki pomiarowe.

Projekt składa się z dwóch elementów: czystego frontendu oraz minimalistycznego mikro-backendu do wsparcia transkodowania surowych plików (np. MXF/ProRes) w tle.

## 🚀 Jak uruchomić projekt lokalnie?

### Opcja 1: Uruchomienie jednym poleceniem (Rekomendowane)
Przygotowałem specjalny skrypt automatyzujący. Z poziomu głównego katalogu (`Sync_DualPlayer`) wpisz po prostu w terminalu:

```bash
./start.sh
```
Skrypt samodzielnie uruchomi w tle oba serwery (Backend i Frontend). Aby zakończyć, wystarczy wcisnąć `Ctrl+C`.

### Opcja 2: Uruchomienie ręczne w dwóch terminalach
Jeśli wolisz mieć oddzielny podgląd na logi serwerów:

### 1. Mikro-Backend (Wymagany do wgrywania MXF)
Ten serwer przetwarza przesyłane wideo z wykorzystaniem wbudowanego w system FFmpeg.

```bash
cd backend
# Aktywacja środowiska wirtualnego:
source venv/bin/activate

# Uruchomienie mikro-serwisu (domyślnie na porcie 8003):
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### 2. Frontend (Interfejs DualPlayer)
Poniższe komendy uruchomią sam odtwarzacz webowy. Aplikacja skonfigurowana jest tak, by proxy Vite przechwytywało i przerzucało ruch do backendu (port `8003`), dlatego musisz mieć oba serwery uruchomione w tle.

```bash
cd frontend
# Uruchomienie serwera deweloperskiego (domyślnie na porcie 3002):
npm run dev
```

Po uruchomieniu wejdź na: **[http://localhost:3002](http://localhost:3002)**

## 📦 Budowa produkcyjna (Frontend)

Jeśli zechcesz wystawić to gdzieś w internecie (tylko frontend obsługujący MP4):
```bash
cd frontend
npm run build
```
Zbudowane pliki wylądują w folderze `dist`.

## 🛠 Technologie
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS v4, Web Workers (porównywanie na klatkach Canvas)
- **Backend:** Python 3, FastAPI, Uvicorn, FFmpeg
