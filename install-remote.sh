#!/bin/bash
# Digital Signage Toolkit - Installer
# Usage: 
#   Latest: curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
#   Specific: curl -sSL ... | sudo bash -s -- -v 2.2.0

set -e

REPO="b-piper/digital-signage-toolkit"
PACKAGE_NAME="dst-toolkit"
TARGET_VERSION="latest"

# Parse args if provided
while getopts "v:" opt; do
  case $opt in
    v) TARGET_VERSION="$OPTARG" ;;
    *) echo "Usage: $0 [-v version]"; exit 1 ;;
  esac
done

echo "============================================"
echo "   Digital Signage Toolkit Installer"
echo "============================================"

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo)"
    exit 1
fi

# Determine API Endpoint
echo "[*] Target Version: $TARGET_VERSION"

if [ "$TARGET_VERSION" = "latest" ]; then
    API_URL="https://api.github.com/repos/${REPO}/releases/latest"
else
    # Ensure 'v' prefix for tag
    if [[ "$TARGET_VERSION" != v* ]]; then
        REF="v$TARGET_VERSION"
    else
        REF="$TARGET_VERSION"
    fi
    API_URL="https://api.github.com/repos/${REPO}/releases/tags/${REF}"
fi

echo "[*] Fetching release info..."
RELEASE_JSON=$(curl -sSL "$API_URL")

# Check if release exists
if echo "$RELEASE_JSON" | grep -q "\"message\": \"Not Found\""; then
    echo "Error: Release not found: $TARGET_VERSION"
    echo "Double-check the version number (available tags)."
    exit 1
fi

# Extract .deb download URL
DOWNLOAD_URL=$(echo "$RELEASE_JSON" | grep "browser_download_url.*\.deb" | cut -d '"' -f 4 | head -n 1)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Error: Could not find .deb asset in release $TARGET_VERSION"
    exit 1
fi

# Extract Clean Version Number from Filename for display
# Expected format: dst-toolkit_X.X.X_amd64.deb
CLEAN_VERSION=$(echo "$DOWNLOAD_URL" | grep -oP 'dst-toolkit_\K[^_]+')
echo "[*] Found package version: $CLEAN_VERSION"

# Download
TEMP_DEB="/tmp/${PACKAGE_NAME}_${CLEAN_VERSION}.deb"
echo "[*] Downloading to $TEMP_DEB..."
curl -sSL -o "$TEMP_DEB" "$DOWNLOAD_URL"

# Install
echo "[*] Installing..."
apt install -y "$TEMP_DEB"

# Cleanup
rm -f "$TEMP_DEB"

echo "============================================"
echo "   Installation Complete!"
echo "   Run 'dst-toolkit' to launch"
echo "============================================"
