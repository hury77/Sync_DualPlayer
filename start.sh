#!/bin/bash

echo "🚀 Uruchamianie Sync DualPlayer..."

# Zatrzymanie procesów w przypadku wyjścia (Ctrl+C)
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# Uruchomienie mikro-backendu w tle
echo "📦 Startowanie mikro-backendu (port 8003)..."
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8003 &
cd ..

# Uruchomienie frontendu w tle
echo "🎨 Startowanie frontendu (port 3002)..."
cd frontend
npm run dev &
cd ..

echo "✅ Wszystko gotowe! Otwórz przeglądarkę pod adresem: http://localhost:3002"
echo "Naciśnij Ctrl+C, aby zatrzymać oba serwery."

# Czekaj na procesy w nieskończoność (do momentu przerwania przez użytkownika)
wait
