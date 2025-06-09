#!/bin/bash
# filepath: /Users/stepan/Documents/projects/django/nanostore/nanostore/install.sh

set -e

echo "=== Setting up Python backend with Poetry ==="
cd backend

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install backend dependencies
poetry install

# Copy .env.example to .env if .env does not exist
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "Copied backend/.env.example to backend/.env. Please edit it with your secrets."
fi

cd ..

echo "=== Setting up Vue frontend with pnpm ==="
cd frontend

# Install pnpm if not present
if ! command -v pnpm &> /dev/null; then
    echo "pnpm not found. Installing pnpm..."
    npm install -g pnpm
fi

# Install frontend dependencies
pnpm install

# Copy .env.example to .env.local if .env.local does not exist
if [ ! -f .env.local ] && [ -f .env.example ]; then
    cp .env.example .env.local
    echo "Copied frontend/.env.example to frontend/.env.local. Please edit it if needed."
fi

cd ..

echo "=== Starting backend WebSocket server with Poetry ==="
cd backend
poetry run python server.py > ../backend_server.log 2>&1 &
cd ..

echo "=== Starting Vue frontend dev server with pnpm ==="
cd frontend
pnpm run dev > ../frontend_server.log 2>&1 &
cd ..

echo "=== All services started! ==="
echo "Backend WebSocket server log: backend_server.log"
echo "Frontend dev server log: frontend_server.log"
echo "Visit http://localhost:5173 (or your Vue dev port) in your browser."