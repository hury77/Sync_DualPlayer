#!/bin/bash

# Zmień katalog na ten, w którym znajduje się skrypt
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/src/backend"

# --- AUTO-UPDATE CHECK ---
NETWORK_DIR="/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO"
if [ -d "$NETWORK_DIR" ]; then
    if [ -f "$NETWORK_DIR/latest_version.txt" ]; then
        REMOTE_VERSION=$(cat "$NETWORK_DIR/latest_version.txt" | tr -d ' \n\r')
        LOCAL_VERSION="1.0"
        if [ -f "version.txt" ]; then
            LOCAL_VERSION=$(cat "version.txt" | tr -d ' \n\r')
        fi
        
        if [ "$REMOTE_VERSION" != "" ] && [ "$LOCAL_VERSION" != "$REMOTE_VERSION" ]; then
            # Pobieramy ścieżkę do naszej własnej aplikacji (.app)
            APP_BUNDLE_PATH="$(dirname "$(dirname "$(dirname "$DIR")")")"
            APP_PARENT_DIR="$(dirname "$APP_BUNDLE_PATH")"
            
            # Generujemy skrypt aktualizujący w tle
            UPDATER_SCRIPT="/tmp/vito_updater.sh"
            DMG_PATH="$NETWORK_DIR/Sync_DualPlayer_v${REMOTE_VERSION}.dmg"
            
            cat <<EOF > "$UPDATER_SCRIPT"
#!/bin/bash
sleep 2
hdiutil attach "$DMG_PATH" -nobrowse -mountpoint /tmp/VITO_Update_Vol
if [ -w "$APP_PARENT_DIR" ] && [ -w "$APP_BUNDLE_PATH" ]; then
    rm -rf "$APP_BUNDLE_PATH"
    cp -a "/tmp/VITO_Update_Vol/Sync_DualPlayer.app" "$APP_PARENT_DIR/"
    TARGET_APP="$APP_BUNDLE_PATH"
else
    rm -rf "$HOME/Desktop/Sync_DualPlayer.app"
    cp -a "/tmp/VITO_Update_Vol/Sync_DualPlayer.app" "$HOME/Desktop/"
    TARGET_APP="$HOME/Desktop/Sync_DualPlayer.app"
fi
hdiutil detach /tmp/VITO_Update_Vol -force
open "\$TARGET_APP"
EOF
            chmod +x "$UPDATER_SCRIPT"
            
            # Odpalamy aktualizator w tle
            nohup "$UPDATER_SCRIPT" > /tmp/vito_updater.log 2>&1 &

            # Pokazujemy użytkownikowi stronę z informacją o trwającej aktualizacji
            HTML_FILE="/tmp/vito_update.html"
            cat <<EOF > "$HTML_FILE"
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>Aktualizacja VITO...</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f9fafb; color: #111827; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); max-width: 500px; text-align: center; border-top: 6px solid #3b82f6; }
        h1 { margin-top: 0; color: #3b82f6; }
        p { line-height: 1.6; color: #4b5563; font-size: 16px; }
        .spinner { margin: 20px auto; width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <div class="spinner"></div>
        <h1>Automatyczna Aktualizacja...</h1>
        <p>Wykryto nową wersję <b>v$REMOTE_VERSION</b> (obecna to v$LOCAL_VERSION).</p>
        <p>Aplikacja pobiera nową wersję i aktualizuje się w tle. <br><br><b>Za kilka sekund nowa wersja VITO włączy się automatycznie.</b> Możesz zamknąć tę kartę.</p>
    </div>
</body>
</html>
EOF
            open "$HTML_FILE"
            exit 0
        fi
    fi
fi
# -------------------------

echo "🚀 Uruchamianie Sync DualPlayer Standalone..."

# Sprawdzenie Pythona
if ! command -v python3 &> /dev/null; then
    echo "Błąd: Wymagany Python 3, którego nie znaleziono w systemie."
    exit 1
fi

# Tworzenie środowiska wirtualnego, jeśli nie istnieje
if [ ! -d "venv" ]; then
    echo "📦 Konfigurowanie środowiska (venv)..."
    python3 -m venv venv
fi

# Aktywacja środowiska
source venv/bin/activate

# Instalacja zależności
echo "📦 Instalowanie zależności..."
pip install -r requirements.txt

# Zatrzymanie serwera w tle po wyjściu
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# Uruchamianie FastAPI z serwowaniem plików statycznych frontendu na 8080
echo "⚙️  Czyszczenie portu i startowanie serwera..."
lsof -ti:8080 | xargs kill -9 2>/dev/null
uvicorn main:app --host 127.0.0.1 --port 8080 &
UVICORN_PID=$!

# Czekamy chwilę na pełne podniesienie serwera
sleep 2

# Otwieramy w przeglądarce
echo "🌐 Otwieranie przeglądarki..."
open "http://localhost:8080"

# Czekamy, aby okno terminala podtrzymywało proces
echo "✅ Aplikacja działa. Możesz zamknąć to okno, aby wyłączyć odtwarzacz."
wait $UVICORN_PID
