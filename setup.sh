#!/bin/bash

set -e

PROJECT_ROOT="$(pwd)"
RELEASE_URL="https://github.com/savka-stepan/nanostore/archive/refs/heads/main.tar.gz"
RELEASE_ARCHIVE="$PROJECT_ROOT/nanostore.tar.gz"
REPO_DIR="$PROJECT_ROOT/nanostore"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"
USER_NAME="$(whoami)"

PYTHON_VERSION="3.12"

echo "=== Installing system dependencies ==="
sudo apt-get update
sudo apt-get install -y git python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip python3-poetry pcscd pcsc-tools libpcsclite1 libccid curl nginx
sudo apt-get install -y nodejs npm

# Ensure user is in plugdev group for device access
sudo usermod -aG plugdev $USER_NAME
sudo usermod -aG dialout $USER_NAME

echo "=== Configuring kernel module blacklist for NFC and USB relay ==="
BLACKLIST_FILE="/etc/modprobe.d/blacklist.conf"
if ! grep -q "install nfc /bin/false" $BLACKLIST_FILE 2>/dev/null; then
    echo "install nfc /bin/false" | sudo tee -a $BLACKLIST_FILE
fi
if ! grep -q "install pn533 /bin/false" $BLACKLIST_FILE 2>/dev/null; then
    echo "install pn533 /bin/false" | sudo tee -a $BLACKLIST_FILE
fi
if ! grep -q "^blacklist spi_ch341" $BLACKLIST_FILE 2>/dev/null; then
    echo "blacklist spi_ch341" | sudo tee -a $BLACKLIST_FILE
fi

# Update initramfs to apply blacklist changes
sudo update-initramfs -u

# Enable and start pcscd for NFC reader support
sudo systemctl enable pcscd
sudo systemctl start pcscd

# Ensure correct permissions for ACR122U NFC reader
sudo tee /etc/udev/rules.d/99-acr122u.rules > /dev/null <<EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", GROUP="plugdev", MODE="0660"
EOF
sudo tee /etc/udev/rules.d/99-usblrb.rules > /dev/null <<EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="5512", GROUP="plugdev", MODE="0660"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", GROUP="plugdev", MODE="0660"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger

# Unload spi_ch341 kernel module to avoid USB relay conflicts
sudo rmmod spi_ch341 || true

# Ensure plugdev users can access pcscd (for Ubuntu 20.04+)
sudo mkdir -p /etc/polkit-1/rules.d/
sudo tee /etc/polkit-1/rules.d/49-pcscd.rules > /dev/null <<EOF
polkit.addRule(function(action, subject) {
    if ((action.id == "org.debian.pcsc-lite.access_pcsc" || action.id == "org.debian.pcsc-lite.access_card") && subject.isInGroup("plugdev")) {
        return polkit.Result.YES;
    }
});
EOF
sudo systemctl restart polkit
sudo systemctl restart pcscd

echo "=== Downloading latest nanostore release archive ==="
# Remove existing directory to ensure fresh download
if [ -d "$REPO_DIR" ]; then
    echo "Removing existing nanostore directory to update to latest version..."
    rm -rf "$REPO_DIR"
fi

wget -O "$RELEASE_ARCHIVE" "$RELEASE_URL"
tar -xzf "$RELEASE_ARCHIVE"
EXTRACTED_DIR=$(tar -tzf "$RELEASE_ARCHIVE" | head -1 | cut -f1 -d"/")
mv "$EXTRACTED_DIR" "$REPO_DIR"
rm "$RELEASE_ARCHIVE"
echo "Latest nanostore version downloaded and extracted."

echo "=== Setting up Python backend ==="
cd "$BACKEND_DIR"

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
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
    echo "pnpm not found. Installing pnpm globally..."
    sudo npm install -g pnpm
fi

# Copy .env.example to .env.local if .env.local does not exist
if [ ! -f .env.local ] && [ -f .env.example ]; then
    cp .env.example .env.local
    echo "Copied frontend/.env.example to frontend/.env.local. Please edit it if needed."
fi

# Build frontend for production
pnpm install
pnpm run build

cd "$REPO_DIR"

echo "=== Configuring nginx ==="
NGINX_CONF="/etc/nginx/sites-available/nanostore"
FRONTEND_DIST="$FRONTEND_DIR/dist"

# Ensure nginx can access the frontend dist directory and all parent directories
echo "=== Setting permissions for nginx to access frontend files ==="
sudo chmod o+x /home
sudo chmod o+x /home/$USER_NAME
sudo chmod o+x /home/$USER_NAME/Documents
sudo chmod o+x /home/$USER_NAME/Documents/nanostore
sudo chmod o+x /home/$USER_NAME/Documents/nanostore/frontend
sudo chmod o+x /home/$USER_NAME/Documents/nanostore/frontend/dist
sudo chmod -R o+r /home/$USER_NAME/Documents/nanostore/frontend/dist

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
After=network.target pcscd.service
Requires=pcscd.service

[Service]
Type=simple
WorkingDirectory=$BACKEND_DIR
ExecStart=/usr/bin/poetry run python server.py
Restart=always
User=$USER_NAME
Environment=PATH=/usr/bin:/bin
Environment=HOME=/home/$USER_NAME

[Install]
WantedBy=multi-user.target
EOL

echo "=== Reloading systemd and enabling backend service ==="
sudo systemctl daemon-reload
sudo systemctl enable nanostore-backend
sudo systemctl restart nanostore-backend

echo "=== Creating systemd service file for card listener ==="

CARD_LISTENER_SERVICE_FILE="/etc/systemd/system/nanostore-card-listener.service"
sudo bash -c "cat > $CARD_LISTENER_SERVICE_FILE" <<EOL
[Unit]
Description=Nanostore Card Listener
After=network.target pcscd.service
Requires=pcscd.service

[Service]
Type=simple
WorkingDirectory=$BACKEND_DIR
ExecStart=/usr/bin/poetry run python card_listener.py
Restart=always
User=$USER_NAME
Environment=PATH=/usr/bin:/bin
Environment=HOME=/home/$USER_NAME

[Install]
WantedBy=multi-user.target
EOL

echo "=== Enabling and starting card listener service ==="
sudo systemctl daemon-reload
sudo systemctl enable nanostore-card-listener
sudo systemctl restart nanostore-card-listener

echo "=== All services started! ==="
echo "Backend: sudo systemctl status nanostore-backend"
echo "Frontend: http://localhost:5000 (served by nginx from $FRONTEND_DIST)"
echo "View backend logs: sudo journalctl -u nanostore-backend -f"
echo "View card listener logs: sudo journalctl -u nanostore-card-listener -f"
echo ""
echo "=== IMPORTANT: Please reboot your system to apply kernel module changes! ==="