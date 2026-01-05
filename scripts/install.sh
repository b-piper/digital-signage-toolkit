#!/bin/bash
# Digital Signage Toolkit - One-Line Installer
# Usage: curl -sL https://example.com/install.sh | sudo bash

set -e

APP_DIR="/opt/dst-toolkit"
REPO_URL="https://github.com/your-org/digital-signage-toolkit.git" # Placeholder
USER_NAME="dst-admin"

echo "==========================================="
echo "   Digital Signage Toolkit Installer v1.0  "
echo "==========================================="

# 1. Check Root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit 1
fi

# 2. Install System Dependencies
echo "[*] Installing System Dependencies (apt)..."
apt-get update
apt-get install -y \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    libxcb-cursor0 \
    libxcb-keysyms1 \
    libxcb-shape0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    scrot \
    git \
    rsync

# 3. Create User (if not exists)
if id "$USER_NAME" &>/dev/null; then
    echo "[*] User $USER_NAME exists."
else
    echo "[*] Creating user $USER_NAME..."
    useradd -m -s /bin/bash $USER_NAME
    usermod -aG sudo $USER_NAME
fi

# 4. Setup Application Directory
echo "[*] Setting up $APP_DIR..."
mkdir -p $APP_DIR
# Sync current directory if running locally, or clone
# For this script we assume it's running from source or we copy
# We'll just ensure permissions for now
chown -R $USER_NAME:$USER_NAME $APP_DIR

# 5. Create Virtual Environment
echo "[*] Creating Python Virtual Environment..."
sudo -u $USER_NAME python3 -m venv $APP_DIR/venv

# 6. Install Python Dependencies
echo "[*] Installing Python Requirements..."
# Create a temporary requirements.txt if sourcing from remote
# For now, assuming requirements.txt exists in $APP_DIR or we write it
cat <<EOF > $APP_DIR/requirements.txt
PyQt6>=6.6.0
qtawesome>=1.3.0
psutil>=5.9.0
requests>=2.31.0
EOF

sudo -u $USER_NAME $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $USER_NAME $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

# 7. Create Desktop Shortcut
echo "[*] Creating Desktop Shortcut..."
cat <<EOF > /usr/share/applications/dst-toolkit.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Digital Signage Toolkit
Comment=Manage Rise Vision Player & System Health
Exec=sudo $APP_DIR/venv/bin/python3 $APP_DIR/main.py
Icon=$APP_DIR/assets/icon.png
Terminal=false
Categories=System;Settings;
EOF

chmod 644 /usr/share/applications/dst-toolkit.desktop

echo "==========================================="
echo "   Installation Complete!                  "
echo "   Run via App Launcher or:                "
echo "   sudo $APP_DIR/venv/bin/python3 $APP_DIR/main.py"
echo "==========================================="
