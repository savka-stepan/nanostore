#!/bin/bash

set -e

PROJECT_ROOT="$(pwd)"
RELEASE_URL="https://github.com/savka-stepan/nanostore/archive/refs/heads/main.tar.gz"
RELEASE_ARCHIVE="$PROJECT_ROOT/nanostore.tar.gz"
REPO_DIR="$PROJECT_ROOT/nanostore"

echo "=== Downloading latest nanostore version ==="
if [ -d "$REPO_DIR" ]; then
    rm -rf "$REPO_DIR"
fi

wget -O "$RELEASE_ARCHIVE" "$RELEASE_URL"
tar -xzf "$RELEASE_ARCHIVE"
EXTRACTED_DIR=$(tar -tzf "$RELEASE_ARCHIVE" | head -1 | cut -f1 -d"/")
mv "$EXTRACTED_DIR" "$REPO_DIR"
rm "$RELEASE_ARCHIVE"

cd "$REPO_DIR"

echo "=== Setting up Vue frontend ==="
cd "$FRONTEND_DIR"

# Build frontend for production
pnpm install
pnpm run build

cd "$REPO_DIR"

echo "=== Restarting services ==="
sudo systemctl restart nanostore-backend
sudo systemctl restart nanostore-card-listener
sudo systemctl restart nginx

echo "=== Update complete! ==="