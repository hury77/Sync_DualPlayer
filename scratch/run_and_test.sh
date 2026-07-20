#!/bin/bash
source backend/venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8005 > /tmp/uvicorn.out 2> /tmp/uvicorn.err &
PID=$!
sleep 2
curl -s -X POST "http://127.0.0.1:8005/api/v1/analyze-elements" \
  -F "frame=@/tmp/debug_frame_1782484077.png" \
  -F "filename=Guest-Pillars-Trailer_IT-IT_Video_1080x1080_30s-Cutdown_2997fps_FrontCTA_01.mp4" \
  -F "timestamp=29.5" \
  -F 'requirements={"country": "IT", "rating": "PEGI 18", "bing": "PS Logo", "bong": "Standard"}' > /tmp/curl.out
kill $PID
cat /tmp/uvicorn.err
