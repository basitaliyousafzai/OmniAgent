#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "====================================================================="
echo "          OmniAgent OS: Autonomous Desktop Workspace Launcher        "
echo "====================================================================="

# 1. Setup Python venv
if [ ! -f ".venv/bin/python" ]; then
    echo "[*] Creating Python virtual environment in .venv..."
    python3 -m venv .venv
    echo "[*] Installing backend dependencies..."
    export PIP_CACHE_DIR="$DIR/.cache/pip"
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r backend/requirements.txt
fi

# 2. Setup Frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "[*] Installing frontend dependencies..."
    cd frontend
    npm install --cache "../.cache/npm"
    cd ..
fi

# 3. Launch Services
echo "[*] Starting OmniAgent OS Backend on port 8000..."
export PYTHONPATH="$DIR/backend"
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "[*] Starting OmniAgent OS Frontend on port 3000..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000 &
FRONTEND_PID=$!
cd ..

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

sleep 2
echo "[*] OmniAgent OS running at http://127.0.0.1:3000"

# Open browser if possible
if which xdg-open > /dev/null; then
    xdg-open http://127.0.0.1:3000
elif which open > /dev/null; then
    open http://127.0.0.1:3000
fi

wait
