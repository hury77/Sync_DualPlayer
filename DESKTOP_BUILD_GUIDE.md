# 🖥️ Przygotowanie Wersji Desktopowej (Electron / Tauri)

Ten dokument opisuje kroki niezbędne do przekształcenia przeglądarkowego **Sync DualPlayer** w natywną aplikację desktopową, którą zespół QA będzie mógł odpalać bezpośrednio z ikony na swoim komputerze.

## Dlaczego wersja desktopowa?
Mimo że aplikacja webowa jest świetna, QA pracujący na dużych plikach MXF/ProRes często preferują aplikacje natywne, ponieważ:
1. Nie ma limitów pamięci nakładanych przez przeglądarkę na zakładki.
2. Można zintegrować własną wersję narzędzia FFmpeg pod maską bez potrzeby posiadania "backendu".
3. Lepsza integracja z systemem plików (możliwość zapisywania plików konfiguracyjnych, zrzutów ekranu rentgena prosto na dysk).

---

## Opcja 1: Użycie Electron.js (Rekomendowana)

Electron to najpopularniejszy framework (używany np. w VS Code, Slack, czy w głównym desktop-app Cradle), który pozwala obudować stronę zrobioną w React w natywne okno z dostępem do Node.js.

### Krok 1: Instalacja Electrona w folderze frontend
```bash
cd frontend
npm install --save-dev electron electron-builder concurrently wait-on cross-env
```

### Krok 2: Konfiguracja Electrona
Utwórz plik `electron/main.js` wewnątrz `frontend`, który stworzy główne okno przeglądarki z włączonym `nodeIntegration`.

```javascript
const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow () {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // W trybie deweloperskim wczytaj localhost, a w produkcyjnym plik index.html z folderu dist
  const url = process.env.VITE_DEV_SERVER_URL 
    ? process.env.VITE_DEV_SERVER_URL 
    : `file://${path.join(__dirname, '../dist/index.html')}`;

  win.loadURL(url);
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
```

### Krok 3: Połączenie z FFmpeg (Pozbycie się zewnętrznego backendu!)
Zamiast wysyłać zapytania sieciowe z plikami MXF do mikro-backendu, z poziomu środowiska Electron można zainstalować bibliotekę `@ffmpeg-installer/ffmpeg` oraz `fluent-ffmpeg` i wykorzystywać wbudowane w OS procesy Node.js do robienia transkodowania bezpośrednio w `StandalonePlayer.tsx` poprzez komunikację IPC! To **całkowicie wyeliminuje zapotrzebowanie na jakikolwiek backend w Pythonie.**

### Krok 4: Skrypty Startowe
Dodaj odpowiednie polecenia w `package.json` w sekcji `"scripts"`:
```json
"electron:start": "cross-env VITE_DEV_SERVER_URL=http://localhost:3002 electron electron/main.js",
"electron:dev": "concurrently -k \"npm run dev\" \"npm run electron:start\"",
"electron:build": "vite build && electron-builder"
```

Uruchomisz wtedy wersję deweloperską na desktopie komendą `npm run electron:dev`.

---

## Dodatkowe modyfikacje po pierwszych testach

Zaraz po przekazaniu pierwszej wersji aplikacji do zespołu, należy być przygotowanym na dodanie kilku usprawnień:
- **Zwiększenie Max Resolution:** W wersji przeglądarkowej worker (diffWorker) często musi minimalizować rozdzielczość klatek, by nie wywołać *Out Of Memory*. W aplikacji desktopowej będziemy mogli zwiększyć limit do 4K.
- **Skróty klawiszowe (Hotkeys):** Zespół na pewno poprosi o możliwość sterowania odtwarzaniem klawiszem Spacji oraz przewijania klatka-po-klatce za pomocą strzałek na klawiaturze (w Electronie można ustawić systemowe hotkeye).
- **Automatyczna aktualizacja (Auto-Updater):** Konfiguracja modułu w Electronie, by QA nie musiało co tydzień ściągać nowych plików `.dmg` / `.exe`.

Zastosowanie frameworka Electron to kolejny, docelowy krok ewolucji dla Sync DualPlayer.
