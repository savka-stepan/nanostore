#!/bin/bash

set -e

PROJECT_ROOT="$(pwd)"
RELEASE_URL="https://github.com/savka-stepan/nanostore/archive/refs/heads/main.tar.gz"
RELEASE_ARCHIVE="$PROJECT_ROOT/nanostore.tar.gz"
REPO_DIR="$PROJECT_ROOT/nanostore"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"

echo "=== Downloading latest nanostore version ==="
if [ -d "$REPO_DIR" ]; then
    echo "Removing existing nanostore directory..."
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

# Reinstall backend dependencies
poetry install --no-root

# Create .env file for backend
echo "=== Creating backend .env file ==="
read -p "Enter IQT_API_EMAIL: " IQT_API_EMAIL
read -s -p "Enter IQT_API_PASSWORD: " IQT_API_PASSWORD
echo

cat > .env << EOF
IQT_API_EMAIL=$IQT_API_EMAIL
IQT_API_PASSWORD=$IQT_API_PASSWORD
EOF
echo "Backend .env file created."

echo "=== Setting up Vue frontend ==="
cd "$FRONTEND_DIR"

# Create .env.local file for frontend
echo "=== Creating frontend .env.local file ==="
cat > .env.local << EOF
VITE_IQT_API_EMAIL=$IQT_API_EMAIL
VITE_IQT_API_PASSWORD=$IQT_API_PASSWORD
EOF
echo "Frontend .env.local file created."

# Reinstall frontend dependencies and build
pnpm install
pnpm run build

echo "=== Restarting services ==="
sudo systemctl restart nanostore-backend
sudo systemctl restart nanostore-card-listener
sudo systemctl restart nginx

echo "=== Update complete! ==="
echo "Backend: sudo systemctl status nanostore-backend"
echo "Frontend: http://localhost:5000"
echo "View backend logs: sudo journalctl -u nanostore-backend -f"
echo "View card listener logs: sudo journalctl -u nanostore-card-listener -f"