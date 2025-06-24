#!/bin/bash

set -e

PROJECT_ROOT="$(pwd)"
REPO_URL="https://github.com/savka-stepan/nanostore"
REPO_DIR="$PROJECT_ROOT/nanostore"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"
USER_NAME="$(whoami)"

PYTHON_VERSION="3.11"

echo "=== Installing system dependencies ==="
sudo apt-get update
sudo apt-get install -y git python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip pcscd pcsc-tools curl nginx

echo "=== Downloading nanostore project from GitHub if not present ==="
if [ ! -d "$REPO_DIR" ]; then
    git clone "$REPO_URL" "$REPO_DIR"
else
    echo "nanostore directory already exists, skipping clone."
fi

echo "=== Configuring kernel module blacklist for NFC ==="
BLACKLIST_FILE="/etc/modprobe.d/blacklist.conf"
if ! grep -q "install nfc /bin/false" $BLACKLIST_FILE 2>/dev/null; then
    echo "install nfc /bin/false" | sudo tee -a $BLACKLIST_FILE
fi
if ! grep -q "install pn533 /bin/false" $BLACKLIST_FILE 2>/dev/null; then
    echo "install pn533 /bin/false" | sudo tee -a $BLACKLIST_FILE
fi

echo "=== Setting up Python backend ==="
cd "$BACKEND_DIR"

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install backend dependencies
poetry install --no-root

# Copy .env.example to .env if .env does not exist
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "Copied backend/.env.example to backend/.env. Please edit it with your secrets."
fi

cd "$REPO_DIR"

echo "=== Setting up Vue frontend ==="
cd "$FRONTEND_DIR"

# Install pnpm if not present
if ! command -v pnpm &> /dev/null; then
    echo "pnpm not found. Installing pnpm..."
    npm install --global pnpm --prefix ~/.local
    export PATH="$HOME/.local/bin:$PATH"
fi

# Copy .env.example to .env.local if .env.local does not exist
if [ ! -f .env.local ] && [ -f .env.example ]; then
    cp .env.example .env.local
    echo "Copied frontend/.env.example to frontend/.env.local. Please edit it if needed."
fi

# Build frontend for production
pnpm run build

cd "$REPO_DIR"

echo "=== Configuring nginx ==="
NGINX_CONF="/etc/nginx/sites-available/nanostore"
FRONTEND_DIST="$FRONTEND_DIR/dist"

sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 5000;
    server_name 127.0.0.1;

    root $FRONTEND_DIST;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOL

# Enable nginx site
sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/nanostore
sudo nginx -t
sudo systemctl restart nginx

echo "=== Creating systemd service file for backend ==="

BACKEND_SERVICE_FILE="/etc/systemd/system/nanostore-backend.service"
sudo bash -c "cat > $BACKEND_SERVICE_FILE" <<EOL
[Unit]
Description=Nanostore Backend WebSocket Server
After=network.target

[Service]
Type=simple
WorkingDirectory=$BACKEND_DIR
ExecStart=$HOME/.local/bin/poetry run python server.py
Restart=always
User=$USER_NAME
Environment=PATH=$HOME/.local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOL

echo "=== Reloading systemd and enabling backend service ==="
sudo systemctl daemon-reload
sudo systemctl enable nanostore-backend
sudo systemctl restart nanostore-backend

echo "=== All services started! ==="
echo "Backend: sudo systemctl status nanostore-backend"
echo "Frontend: http://localhost:5000 (served by nginx from $FRONTEND_DIST)"
echo "View backend logs: sudo journalctl -u nanostore-backend -f"
echo ""
echo "=== IMPORTANT: Please reboot your system to apply kernel module changes! ==="