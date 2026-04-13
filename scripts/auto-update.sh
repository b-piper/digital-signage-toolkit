#!/bin/bash
# Digital Signage Toolkit - Auto Update Script
# Checks GitHub for new releases and auto-installs if available
# Runs daily via systemd timer at 3:00 AM

set -e

REPO="b-piper/digital-signage-toolkit"
VERSION_FILE="/opt/dst-toolkit/VERSION"
LOG_FILE="/var/log/dst-toolkit/auto-update.log"
LOCK_FILE="/var/run/dst-auto-update.lock"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" >> "$LOG_FILE"
}

# Prevent concurrent runs
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    log "ERROR: Another update is already running"
    exit 1
fi

log "INFO: Starting update check..."

# Get current version
if [ -f "$VERSION_FILE" ]; then
    CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
else
    CURRENT="0.0.0"
    log "INFO: No version file found, assuming version 0.0.0"
fi

# Get latest version from GitHub API
LATEST=$(curl -sSL --connect-timeout 10 --max-time 30 \
    "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null \
    | grep '"tag_name"' \
    | head -1 \
    | cut -d'"' -f4 \
    | tr -d 'v')

if [ -z "$LATEST" ]; then
    log "ERROR: Could not fetch latest version from GitHub"
    exit 1
fi

log "INFO: Current version: $CURRENT, Latest version: $LATEST"

# Compare versions (simple string comparison works for semver)
if [ "$LATEST" = "$CURRENT" ]; then
    log "INFO: Already up to date (v$CURRENT)"
    exit 0
fi

# Version comparison function
version_gt() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

if ! version_gt "$LATEST" "$CURRENT"; then
    log "INFO: Current version ($CURRENT) is newer or equal to latest ($LATEST)"
    exit 0
fi

log "INFO: New version available! Updating from v$CURRENT to v$LATEST"

# Create backup of current installation
BACKUP_DIR="/opt/dst-toolkit-backup-$(date +%Y%m%d%H%M%S)"
if [ -d "/opt/dst-toolkit" ]; then
    cp -r /opt/dst-toolkit "$BACKUP_DIR"
    log "INFO: Created backup at $BACKUP_DIR"
fi

# Download the self-extracting installer from the latest release
INSTALLER_FILE=$(mktemp --suffix=.sh)
INSTALLER_URL=$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null | grep "browser_download_url" | grep "install\.sh" | head -1 | cut -d '"' -f 4)

if [ -n "$INSTALLER_URL" ] && curl -sSL --connect-timeout 10 --max-time 300 "$INSTALLER_URL" -o "$INSTALLER_FILE" 2>/dev/null; then
    
    chmod +x "$INSTALLER_FILE"
    
    # Run the self-extracting installer (we're already root via systemd)
    if bash "$INSTALLER_FILE" >> "$LOG_FILE" 2>&1; then
        echo "$LATEST" > "$VERSION_FILE"
        log "SUCCESS: Updated to v$LATEST"
        
        # Clean up old backups (keep last 3)
        ls -dt /opt/dst-toolkit-backup-* 2>/dev/null | tail -n +4 | xargs rm -rf 2>/dev/null || true
        
        # Optional: Restart the toolkit if running
        # systemctl restart dst-toolkit 2>/dev/null || true
    else
        log "ERROR: Update failed during installation, restoring backup"
        if [ -d "$BACKUP_DIR" ]; then
            rm -rf /opt/dst-toolkit
            mv "$BACKUP_DIR" /opt/dst-toolkit
            log "INFO: Backup restored"
        fi
        rm -f "$INSTALLER_FILE"
        exit 1
    fi
    
    rm -f "$INSTALLER_FILE"
else
    log "ERROR: Failed to download installer from release"
    rm -f "$INSTALLER_FILE"
    exit 1
fi

log "INFO: Update complete"

