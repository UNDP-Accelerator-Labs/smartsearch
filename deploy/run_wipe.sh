#!/bin/sh

cd "/app/public"
python -m http.server -b "0.0.0.0" -p "${PORT}" &

sleep 30

/bin/sh -c /app/wipe.sh &> /app/public/output.txt

while true; do
  sleep 60
done
