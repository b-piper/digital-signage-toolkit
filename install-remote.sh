#!/bin/bash
# Digital Signage Toolkit - Remote Installer
# One-line install: curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
#
# This script:
#   1. Detects the latest release from GitHub
#   2. Downloads the .deb package
#   3. Installs it with apt
#   4. Verifies the installation

set -euo pipefail

REPO="b-piper/digital-signage-toolkit"
LOG_FILE="/var/log/dst-toolkit/install.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "$1"
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" >> "$LOG_FILE" 2>/dev/null || true
}

die() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    die "This script must be run as root. Use: curl -sSL ... | sudo bash"
fi

log "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
log "${GREEN}║   Digital Signage Toolkit — Remote Installer      ║${NC}"
log "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
log ""

# Check dependencies
for cmd in curl apt-get dpkg-deb; do
    if ! command -v "$cmd" &>/dev/null; then
        die "Required command '$cmd' not found. Is this a Debian/Ubuntu system?"
    fi
done

# Get current version (if installed)
VERSION_FILE="/opt/dst-toolkit/VERSION"
if [ -f "$VERSION_FILE" ]; then
    CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
    log "Current version: ${YELLOW}v${CURRENT}${NC}"
else
    CURRENT="0.0.0"
    log "No existing installation detected — fresh install."
fi

# Fetch latest release info from GitHub
log "Checking for latest release..."
RELEASE_JSON=$(curl -sSL --connect-timeout 10 --max-time 30 \
    "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null) \
    || die "Could not reach GitHub API. Check internet connectivity."

LATEST=$(echo "$RELEASE_JSON" | grep '"tag_name"' | head -1 | cut -d'"' -f4 | tr -d 'v')
if [ -z "$LATEST" ]; then
    die "Could not determine latest version from GitHub."
fi

log "Latest version: ${GREEN}v${LATEST}${NC}"

# Check if already up to date
if [ "$LATEST" = "$CURRENT" ]; then
    log "${GREEN}Already up to date (v${CURRENT}). Nothing to do.${NC}"
    exit 0
fi

# Get download URL for .deb package
DEB_URL=$(echo "$RELEASE_JSON" | grep "browser_download_url" | grep "\.deb" | head -1 | cut -d'"' -f4)
if [ -z "$DEB_URL" ]; then
    die "No .deb package found in the latest release. Check GitHub releases."
fi

log "Downloading: ${DEB_URL}..."

# Download to temp file
DEB_FILE=$(mktemp --suffix=.deb)
trap "rm -f '$DEB_FILE'" EXIT

curl -sSL --connect-timeout 10 --max-time 300 "$DEB_URL" -o "$DEB_FILE" \
    || die "Failed to download .deb package."

# Verify it's a valid deb
if ! dpkg-deb -I "$DEB_FILE" >/dev/null 2>&1; then
    die "Downloaded file is not a valid Debian package. It may be corrupted."
fi

log "Installing Digital Signage Toolkit v${LATEST}..."

# Install
if apt-get install -y "$DEB_FILE" >> "$LOG_FILE" 2>&1; then
    echo "$LATEST" > "$VERSION_FILE"
    log ""
    log "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
    log "${GREEN}║   Installation Complete — v${LATEST}                    ║${NC}"
    log "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
    log ""
    log "Verify with:  ${YELLOW}dst-toolkit --status${NC}"
    log "Launch GUI:   ${YELLOW}dst-toolkit${NC}"
    log "Health check: ${YELLOW}curl http://localhost:8080/health${NC}"
else
    die "Package installation failed. Check ${LOG_FILE} for details."
fi
