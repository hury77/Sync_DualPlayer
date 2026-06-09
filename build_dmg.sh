#!/bin/bash

APP_NAME="Sync_DualPlayer"
APP_DIR="${APP_NAME}.app"
SRC_DIR="${APP_DIR}/Contents/MacOS/src"

echo "🚀 Budowanie najnowszej wersji aplikacji (v2.0)..."

# 1. Zbudowanie frontendu
echo "📦 Kompilacja Frontendu..."
cd frontend
npm run build
cd ..

# 2. Skopiowanie frontendu do .app
echo "📂 Aktualizacja plików frontendu w .app..."
rm -rf "${SRC_DIR}/frontend_dist"
cp -r frontend/dist "${SRC_DIR}/frontend_dist"

# 3. Skopiowanie backendu do .app (z pominięciem zbędnych folderów)
echo "📂 Aktualizacja skryptów backendu w .app..."
rm -rf "${SRC_DIR}/backend"
mkdir -p "${SRC_DIR}/backend"
cp backend/main.py "${SRC_DIR}/backend/"
cp backend/requirements.txt "${SRC_DIR}/backend/"
if [ -f "backend/ffmpeg" ]; then
    cp backend/ffmpeg "${SRC_DIR}/backend/"
fi

# 4. Nadanie uprawnień
chmod +x "${APP_DIR}/Contents/MacOS/Sync_DualPlayer"

# 5. Tworzenie pliku DMG
echo "💿 Generowanie pliku DMG..."
DMG_NAME="${APP_NAME}_v2.0.dmg"
rm -f "$DMG_NAME"
hdiutil create -volname "${APP_NAME}" -srcfolder "${APP_DIR}" -ov -format UDZO "$DMG_NAME"

echo "✅ Gotowe! Plik $DMG_NAME został wygenerowany i jest gotowy do dystrybucji."
