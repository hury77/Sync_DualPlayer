#!/bin/bash
set -e

# Setup server in background
cd backend
source venv/bin/activate
uvicorn main:app --port 8004 &
SERVER_PID=$!
sleep 3

echo "=== TEST 1: delete_file and clear_qa_assets permissions ==="
touch /tmp/fake_file.mp4
chmod 000 /tmp/fake_file.mp4
# my files_db is empty because it restarted. Let's create a python script to test.
