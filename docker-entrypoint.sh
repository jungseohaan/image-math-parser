#!/bin/bash
set -e

# Start Next.js frontend in background
cd /app/frontend
node server.js &

# Start Flask backend with gunicorn
cd /app
exec gunicorn --bind 0.0.0.0:4001 --workers 2 --threads 4 --timeout 120 app:app
