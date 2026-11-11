#!/bin/bash

echo "========================================="
echo "        AlgoScan / StockAI Pulse"
echo "========================================="

# Check dependencies
command -v python3 >/dev/null 2>&1 || { echo >&2 "python3 is required but it's not installed.  Aborting."; exit 1; }
command -v node >/dev/null 2>&1 || { echo >&2 "node is required but it's not installed.  Aborting."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo >&2 "npm is required but it's not installed.  Aborting."; exit 1; }

# Setup .env
if [ ! -f backend/.env ]; then
    if [ -f backend/.env.example ]; then
        echo "Copying backend/.env.example to backend/.env..."
        cp backend/.env.example backend/.env
    else
        echo "Warning: backend/.env.example not found"
    fi
fi

# Trap SIGINT and SIGTERM to kill background processes
trap "kill 0" SIGINT SIGTERM EXIT

echo "Starting Backend..."
cd backend && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo "Starting Frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo "Waiting for services to initialize..."
sleep 2

echo "Opening browser..."
if which xdg-open > /dev/null; then
  xdg-open http://localhost:5173
elif which open > /dev/null; then
  open http://localhost:5173
else
  echo "Could not detect web browser to open automatically. Please visit http://localhost:5173"
fi

echo "Running... Press Ctrl+C to stop."
wait
