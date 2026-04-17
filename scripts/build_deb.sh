#!/bin/bash
# Digital Signage Toolkit - Debian Package Builder
# Usage: ./scripts/build_deb.sh [version]

VERSION=${1:-"1.0.0"}
ARCH="amd64"
PKG_NAME="dst-toolkit"
FULL_NAME="${PKG_NAME}_${VERSION}_${ARCH}"
BUILD_DIR="build/${FULL_NAME}"

# Ensure we're in the project root
if [ ! -f "main.py" ]; then
    echo "Error: Please run this from the project root (e.g., ./scripts/build_deb.sh)"
    exit 1
fi

echo "==========================================="
echo "   Building ${FULL_NAME}.deb "
echo "==========================================="

# 1. Clean previous build
echo "[*] Cleaning build directory..."
rm -rf build
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/opt/${PKG_NAME}"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps"

# 2. Copy Source Code
echo "[*] Copying source code..."
# Exclude build dir, .git, .venv, __pycache__
rsync -av . "${BUILD_DIR}/opt/${PKG_NAME}/" \
    --exclude "build" \
    --exclude ".git" \
    --exclude ".venv" \
    --exclude "venv" \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    --exclude "*.md" \
    --exclude "tests" \
    --exclude "docs"

# 3. Create Control File
echo "[*] Creating control file..."
cat <<EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-venv, python3-pip, python3-pyqt6, python3-psutil, scrot, libxcb-cursor0, libxcb-keysyms1, libxcb-shape0, libxcb-icccm4, libxcb-image0, libxcb-randr0, libxcb-render-util0, libxcb-xinerama0, libxkbcommon-x11-0
Maintainer: IT Department <it@southwesterncc.edu>
Description: Digital Signage Toolkit
 A comprehensive management utility for Rise Vision Player kiosks.
 Includes health monitoring, remote screenshots, and system healing.
EOF

# 4. Create Post-Install Script
# NOTE: Cannot call apt-get here — dpkg holds the database lock during postinst.
# All apt dependencies are declared in the Depends line above and resolved by dpkg/apt
# BEFORE this script runs. This script only handles venv/pip setup.
echo "[*] Creating postinst script..."
cat <<EOF > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

APP_DIR="/opt/${PKG_NAME}"
LOG="/var/log/dst-toolkit-install.log"

case "\$1" in
    configure)
        echo "[DST] Configuring Digital Signage Toolkit..." | tee "\$LOG"
        
        # Create venv if not exists
        echo "[DST] Setting up Python Virtual Environment..." | tee -a "\$LOG"
        if [ ! -d "\$APP_DIR/venv" ]; then
            python3 -m venv --system-site-packages "\$APP_DIR/venv" >> "\$LOG" 2>&1
        fi
        
        # Install Pip Requirements
        echo "[DST] Installing Python Dependencies..." | tee -a "\$LOG"
        "\$APP_DIR/venv/bin/pip" install --upgrade pip >> "\$LOG" 2>&1 || true
        # Install pinned runtime dependencies
        if [ -f "\$APP_DIR/requirements-runtime.txt" ]; then
            "\$APP_DIR/venv/bin/pip" install -r "\$APP_DIR/requirements-runtime.txt" >> "\$LOG" 2>&1 || true
        else
            echo "WARNING: requirements-runtime.txt not found, falling back to unpinned install" | tee -a "\$LOG"
            "\$APP_DIR/venv/bin/pip" install qtawesome requests >> "\$LOG" 2>&1 || true
        fi
        
        # Fix permissions of app
        chown -R root:root "\$APP_DIR"
        chmod -R 755 "\$APP_DIR"
        
        # Create Global Log Directory with secure permissions
        echo "[DST] Setting up /var/log/dst-toolkit..." | tee -a "\$LOG"
        mkdir -p /var/log/dst-toolkit
        
        # Create dst-toolkit group if it doesn't exist
        if ! getent group dst-toolkit > /dev/null 2>&1; then
            groupadd --system dst-toolkit
        fi
        
        # Set secure permissions: root owns, dst-toolkit group can read/write
        chown root:dst-toolkit /var/log/dst-toolkit
        chmod 750 /var/log/dst-toolkit
        
        # Add the installing user to dst-toolkit group (if SUDO_USER is set)
        if [ -n "\$SUDO_USER" ]; then
            usermod -aG dst-toolkit "\$SUDO_USER" 2>/dev/null || true
        fi
        
        # Create VERSION file
        echo "[DST] Creating version file..." | tee -a "\$LOG"
        echo "${VERSION}" > "\$APP_DIR/VERSION"
        
        # Install systemd units for auto-update
        echo "[DST] Setting up auto-update timer..." | tee -a "\$LOG"
        if [ -d /etc/systemd/system ]; then
            cp "\$APP_DIR/debian/dst-auto-update.timer" /etc/systemd/system/ 2>/dev/null || true
            cp "\$APP_DIR/debian/dst-auto-update.service" /etc/systemd/system/ 2>/dev/null || true
            # systemd requires unit files to NOT be executable
            chmod 644 /etc/systemd/system/dst-auto-update.timer 2>/dev/null || true
            chmod 644 /etc/systemd/system/dst-auto-update.service 2>/dev/null || true
            systemctl daemon-reload 2>/dev/null || true
            systemctl enable dst-auto-update.timer 2>/dev/null || true
            systemctl start dst-auto-update.timer 2>/dev/null || true
        fi
        
        # Make scripts executable
        chmod +x "\$APP_DIR/scripts/"*.sh 2>/dev/null || true
        
        echo "[DST] Installation complete!" | tee -a "\$LOG"
    ;;
esac

exit 0
EOF



chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# 5. Create GUI Launcher Wrapper
echo "[*] Creating GUI Launcher Wrapper..."
cat <<EOF > "${BUILD_DIR}/usr/bin/${PKG_NAME}-gui"
#!/bin/bash
# Wrapper to launch DST as root from GUI, preserving display environment
if [ -z "\$DISPLAY" ]; then
    export DISPLAY=:0
fi
# Use pkexec to run as root, passing necessary X11/Wayland variables
pkexec env DISPLAY=\$DISPLAY XAUTHORITY=\$XAUTHORITY /opt/${PKG_NAME}/venv/bin/python /opt/${PKG_NAME}/main.py
EOF
chmod 755 "${BUILD_DIR}/usr/bin/${PKG_NAME}-gui"

# 6. Create Desktop Entry
echo "[*] Creating Desktop Entry..."
cat <<EOF > "${BUILD_DIR}/usr/share/applications/${PKG_NAME}.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Digital Signage Toolkit
Comment=Manage Rise Vision Player & System Health
Exec=${PKG_NAME}-gui
Icon=${PKG_NAME}
Terminal=false
Categories=System;Settings;
EOF

# 7. Create Symlink Launcher (CLI)
echo "[*] Creating CLI Launcher Symlink..."
# We create a script in /usr/bin for CLI usage (sudo)
cat <<EOF > "${BUILD_DIR}/usr/bin/${PKG_NAME}"
#!/bin/bash
exec sudo /opt/${PKG_NAME}/venv/bin/python /opt/${PKG_NAME}/main.py "\$@"
EOF
chmod 755 "${BUILD_DIR}/usr/bin/${PKG_NAME}"

# 7. Icon Handling
echo "[*] Installing application icon..."
if [ -f "digital_signage_toolkit/branding/SCC Digital Signage Toolkit.png" ]; then
    cp "digital_signage_toolkit/branding/SCC Digital Signage Toolkit.png" "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps/${PKG_NAME}.png"
    echo "    Icon installed from branding folder"
else
    echo "    WARNING: Icon not found in branding folder"
fi

# 8. Build Package
echo "[*] Building .deb package..."
dpkg-deb --build "${BUILD_DIR}"

mv "build/${FULL_NAME}.deb" .

# 9. Generate Self-Extracting Installer
# Creates a SINGLE install.sh file with the .deb embedded inside it.
# The technician only needs this one file — no separate .deb download required.
# Uses zenity (pre-installed on Ubuntu GNOME) for a fully graphical install experience.
# Technician flow: right-click → Properties → Allow Executing → double-click → enter password → done.
echo "[*] Generating self-extracting install.sh..."

# Write the shell script portion of the installer
cat <<'INSTALL_EOF' > install.sh
#!/bin/bash
# ============================================================
# Digital Signage Toolkit - Self-Extracting Installer
# ============================================================
# This file contains the .deb package embedded within it.
# Double-click this file to install (after marking executable).
# Or run from terminal: sudo bash install.sh
# ============================================================

LOG_FILE="/tmp/dst-toolkit-install.log"

# --- Helper: detect if zenity is available for GUI mode ---
HAS_ZENITY=false
if command -v zenity >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    HAS_ZENITY=true
fi

show_error() {
    if $HAS_ZENITY; then
        zenity --error --title="DST Install Error" --text="$1" --width=400 2>/dev/null
    fi
    echo "ERROR: $1" >&2
    exit 1
}

show_info() {
    if $HAS_ZENITY; then
        zenity --info --title="Digital Signage Toolkit" --text="$1" --width=400 2>/dev/null
    fi
    echo "$1"
}

# --- If not root, re-launch with pkexec (GUI password prompt) ---
if [ "$EUID" -ne 0 ]; then
    if command -v pkexec >/dev/null 2>&1; then
        # pkexec runs the script as root with a GUI password dialog
        pkexec env DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" bash "$0" "$@"
        exit $?
    else
        show_error "This installer must be run as root.\n\nOpen a terminal and run:\n  sudo bash install.sh"
    fi
fi

# --- We are root from here ---

# Extract the embedded .deb package from this script
ARCHIVE_LINE=$(grep -an '^__DEB_ARCHIVE__$' "$0" | tail -1 | cut -d: -f1)
if [ -z "$ARCHIVE_LINE" ]; then
    show_error "Could not find embedded package data.\n\nThis installer file may be corrupted."
fi

DEB_FILE=$(mktemp /tmp/dst-toolkit_XXXXXX.deb)
trap "rm -f '$DEB_FILE'" EXIT

tail -n +"$((ARCHIVE_LINE + 1))" "$0" > "$DEB_FILE"

# Verify the extracted file is a valid deb
if ! dpkg-deb -I "$DEB_FILE" >/dev/null 2>&1; then
    show_error "Embedded package is not a valid Debian package.\n\nThis installer file may be corrupted."
fi

DEB_NAME="dst-toolkit.deb"

do_install() {
    echo "# Updating package lists..." ; echo "10"
    apt-get update -qq >> "$LOG_FILE" 2>&1

    echo "# Installing Digital Signage Toolkit..." ; echo "40"
    apt-get install -y -qq "$DEB_FILE" >> "$LOG_FILE" 2>&1
    INSTALL_RESULT=$?

    if [ $INSTALL_RESULT -ne 0 ]; then
        echo "# Resolving dependencies..." ; echo "60"
        dpkg -i "$DEB_FILE" >> "$LOG_FILE" 2>&1 || true
        apt-get install -f -y -qq >> "$LOG_FILE" 2>&1
    fi

    echo "# Verifying installation..." ; echo "90"
    dpkg -s dst-toolkit >> "$LOG_FILE" 2>&1
    VERIFY_RESULT=$?

    echo "# Done" ; echo "100"
    return $VERIFY_RESULT
}

# --- Run installation with GUI progress bar or terminal output ---
echo "=== DST Install Log $(date) ===" > "$LOG_FILE"

if $HAS_ZENITY; then
    do_install | zenity --progress \
        --title="Installing Digital Signage Toolkit" \
        --text="Preparing..." \
        --percentage=0 \
        --auto-close \
        --no-cancel \
        --width=400 2>/dev/null

    # Check if installation succeeded
    if dpkg -s dst-toolkit >/dev/null 2>&1; then
        zenity --info \
            --title="Installation Complete" \
            --text="Digital Signage Toolkit has been installed successfully!\n\nYou can launch it from the Applications menu\nor by running: dst-toolkit" \
            --width=400 2>/dev/null
    else
        zenity --error \
            --title="Installation Failed" \
            --text="Installation encountered an error.\n\nCheck the log at:\n$LOG_FILE" \
            --width=400 2>/dev/null
        exit 1
    fi
else
    # Terminal-only mode
    echo "==========================================="
    echo "   Installing Digital Signage Toolkit"
    echo "==========================================="

    echo "[1/4] Extracting embedded package..."
    echo "       OK — extracted to temp file"

    echo "[2/4] Updating package lists..."
    apt-get update -qq

    echo "[3/4] Installing package and dependencies..."
    apt-get install -y "$DEB_FILE" || {
        echo "[3/4] Retrying with dpkg + apt-get -f..."
        dpkg -i "$DEB_FILE" || true
        apt-get install -f -y -qq
    }

    echo "[4/4] Verifying installation..."
    if dpkg -s dst-toolkit >/dev/null 2>&1; then
        echo "==========================================="
        echo "   Installation Complete!"
        echo ""
        echo "   Launch from Applications menu or run:"
        echo "     dst-toolkit"
        echo "==========================================="
    else
        echo "==========================================="
        echo "   Installation FAILED"
        echo "   Check log: $LOG_FILE"
        echo "==========================================="
        exit 1
    fi
fi

# Exit before the binary payload
exit 0
__DEB_ARCHIVE__
INSTALL_EOF

# Append the actual .deb binary to the end of install.sh
cat "${FULL_NAME}.deb" >> install.sh
chmod 755 install.sh

# Show final size info
INSTALLER_SIZE=$(du -h install.sh | cut -f1)
echo "==========================================="
echo "   Build Complete!"
echo "   Self-extracting installer: install.sh (${INSTALLER_SIZE})"
echo "   Standalone .deb also available: ${FULL_NAME}.deb"
echo "==========================================="

