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
Depends: python3
Maintainer: IT Department <it@southwesterncc.edu>
Description: Digital Signage Toolkit
 A comprehensive management utility for Rise Vision Player kiosks.
 Includes health monitoring, remote screenshots, and system healing.
EOF

# 4. Create Post-Install Script
# This handles all dependency installation and virtualenv setup
echo "[*] Creating postinst script..."
cat <<EOF > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

APP_DIR="/opt/${PKG_NAME}"
LOG="/var/log/dst-toolkit-install.log"

case "\$1" in
    configure)
        echo "[DST] Installing Digital Signage Toolkit..." | tee "\$LOG"
        
        # Install system dependencies
        echo "[DST] Updating package lists..." | tee -a "\$LOG"
        apt-get update -qq >> "\$LOG" 2>&1
        
        echo "[DST] Installing system dependencies..." | tee -a "\$LOG"
        apt-get install -y -qq \
            python3-venv \
            python3-pip \
            python3-pyqt6 \
            python3-psutil \
            scrot \
            libxcb-cursor0 \
            libxcb-keysyms1 \
            libxcb-shape0 \
            libxcb-icccm4 \
            libxcb-image0 \
            libxcb-randr0 \
            libxcb-render-util0 \
            libxcb-xinerama0 \
            libxkbcommon-x11-0 >> "\$LOG" 2>&1
        
        # Create venv if not exists
        echo "[DST] Setting up Python Virtual Environment..." | tee -a "\$LOG"
        if [ ! -d "\$APP_DIR/venv" ]; then
            python3 -m venv --system-site-packages "\$APP_DIR/venv"
        fi
        
        # Install Pip Requirements
        echo "[DST] Installing Python Dependencies..." | tee -a "\$LOG"
        "\$APP_DIR/venv/bin/pip" install --upgrade pip >> "\$LOG" 2>&1
        # Install pinned runtime dependencies
        if [ -f "\$APP_DIR/requirements-runtime.txt" ]; then
            "\$APP_DIR/venv/bin/pip" install -r "\$APP_DIR/requirements-runtime.txt" >> "\$LOG" 2>&1
        else
            echo "WARNING: requirements-runtime.txt not found, falling back to unpinned install" | tee -a "\$LOG"
            "\$APP_DIR/venv/bin/pip" install qtawesome requests >> "\$LOG" 2>&1
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
            systemctl daemon-reload
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
if [ -f "branding/SCC Digital Signage Toolkit.png" ]; then
    cp "branding/SCC Digital Signage Toolkit.png" "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps/${PKG_NAME}.png"
    echo "    Icon installed from branding folder"
else
    echo "    WARNING: Icon not found in branding folder"
fi

# 8. Build Package
echo "[*] Building .deb package..."
dpkg-deb --build "${BUILD_DIR}"

mv "build/${FULL_NAME}.deb" .

# 9. Generate Install Script
echo "[*] Generating install.sh..."
cat <<'INSTALL_EOF' > install.sh
#!/bin/bash
# Digital Signage Toolkit - One-Step Installer
# Usage: sudo bash install.sh
set -e

if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo bash install.sh)"
    exit 1
fi

DEB_FILE=$(ls dst-toolkit_*.deb 2>/dev/null | head -1)

if [ -z "$DEB_FILE" ]; then
    echo "Error: No .deb file found in current directory."
    echo "Place this script in the same folder as the dst-toolkit_*.deb file."
    exit 1
fi

echo "==========================================="
echo "   Installing Digital Signage Toolkit"
echo "   Package: $DEB_FILE"
echo "==========================================="

echo "[1/3] Updating package lists..."
apt-get update -qq

echo "[2/3] Installing package..."
dpkg -i "$DEB_FILE" || true

echo "[3/3] Resolving dependencies..."
apt-get install -f -y -qq

echo "==========================================="
echo "   Installation Complete!"
echo "   Launch from Applications menu or run:"
echo "     dst-toolkit-gui"
echo "==========================================="
INSTALL_EOF
chmod 755 install.sh

echo "==========================================="
echo "   Build Complete: ${FULL_NAME}.deb "
echo "   Installer:      install.sh"
echo "==========================================="
