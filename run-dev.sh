#!/bin/bash
# Development server startup script

# Start Flask backend
echo "Starting Flask backend..."
cd flask
python app.py &
FLASK_PID=$!
cd ..

# Start Next.js frontend
# PORT를 명시적으로 설정하여 시스템 환경 변수 override
echo "Starting Next.js frontend..."
cd client
PORT=3000 npm run dev &
NEXT_PID=$!
cd ..

echo ""
echo "==================================="
echo "  Backend:  http://localhost:4001"
echo "  Frontend: http://localhost:3000"
echo "==================================="
echo ""
echo "Press Ctrl+C to stop both servers"

# Trap Ctrl+C to kill both processes
trap "kill $FLASK_PID $NEXT_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for both processes
wait
