#!/bin/bash
# Digital Signage Toolkit - One-Line Installer
# Usage: curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
#
# This script:
# 1. Downloads the latest .deb from GitHub Releases
# 2. Installs it with apt
# 3. Cleans up

set -e

REPO="b-piper/digital-signage-toolkit"
PACKAGE_NAME="dst-toolkit"

echo "============================================"
echo "   Digital Signage Toolkit Installer"
echo "============================================"

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo)"
    exit 1
fi

# Get latest release URL
echo "[*] Fetching latest release..."
LATEST_URL=$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" | \
    grep "browser_download_url.*\.deb" | \
    cut -d '"' -f 4)

if [ -z "$LATEST_URL" ]; then
    echo "Error: Could not find latest release"
    exit 1
fi

VERSION=$(echo "$LATEST_URL" | grep -oP 'dst-toolkit_\K[^_]+')
echo "[*] Latest version: $VERSION"

# Download
TEMP_DEB="/tmp/${PACKAGE_NAME}_${VERSION}.deb"
echo "[*] Downloading package..."
curl -sSL -o "$TEMP_DEB" "$LATEST_URL"

# Install
echo "[*] Installing..."
apt install -y "$TEMP_DEB"

# Cleanup
rm -f "$TEMP_DEB"

echo "============================================"
echo "   Installation Complete!"
echo "   Run 'dst-toolkit' to launch"
echo "============================================"
