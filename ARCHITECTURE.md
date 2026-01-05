# Digital Signage Toolkit - Architecture Documentation

## Project Overview

The Digital Signage Toolkit is a professional GUI application for provisioning and maintaining Ubuntu Digital Signage Kiosks. Built with Python 3.8+ and PyQt6, it provides a centralized management interface for system administration tasks, software installation, monitoring, and system restoration.

---

## Directory Structure

```
Digital Signage Toolkit/
│
├── digital_signage_toolkit/          # Main Python package
│   ├── __init__.py                   # Package initialization
│   ├── __main__.py                    # Package entry point
│   └── main.py                        # Application entry point
│
├── gui/                               # GUI components
│   ├── __init__.py
│   ├── main_window.py                 # Main application window
│   └── widgets.py                     # Custom GUI widgets
│
├── core/                              # Core business logic
│   ├── __init__.py
│   ├── system_ops.py                  # System operations (apt, hostname, display)
│   ├── software_installer.py          # Software installation (TeamViewer, Rise Vision)
│   ├── watchdog.py                    # Watchdog management (cron jobs)
│   ├── timeshift_manager.py           # System snapshot/restore management
│   └── hardware_monitor.py            # Hardware health monitoring
│
├── utils/                             # Utility modules
│   ├── __init__.py
│   ├── config.py                      # Configuration management
│   ├── sudo_handler.py                # Sudo privilege management
│   ├── validators.py                  # Input validation and sanitization
│   ├── logger.py                      # Centralized logging and audit trail
│   ├── file_utils.py                  # File operations (downloads, checksums)
│   └── preflight_checks.py            # Pre-installation validation
│
├── tests/                             # Unit tests
│   ├── __init__.py
│   ├── test_validators.py             # Validator function tests
│   └── test_file_utils.py             # File utility tests
│
├── scripts/                           # Deployment and utility scripts
│   └── health_check.sh                # Post-deployment health check
│
├── debian/                            # Debian package configuration
│   ├── changelog                      # Package changelog
│   ├── compat                         # Debian compatibility
│   ├── control                        # Package metadata
│   ├── rules                          # Build rules
│   ├── digital-signage-toolkit.desktop # Desktop launcher
│   ├── digital-signage-toolkit.png    # Application icon
│   └── logrotate.digital-signage-toolkit # Log rotation config
│
├── deployment-ready/                  # Pre-packaged deployment folder
│   └── [Mirrors main structure]      # Copy of source files for deployment
│
├── main.py                            # Root-level entry point (legacy)
├── setup.py                           # Python package setup script
├── requirements.txt                   # Python dependencies
├── config.json                        # Default configuration file
├── pytest.ini                         # Pytest configuration
│
├── install-digital-signage-toolkit.sh # Main installation script
├── INSTALL_FROM_USB.sh                # USB-based installation script
├── UNINSTALL.sh                       # Uninstallation script
├── PREPARE_DEPLOYMENT.bat             # Windows deployment preparer
│
├── README.md                          # Project overview and features
├── SETUP_INSTRUCTIONS.md              # Technician setup guide
├── CHANGELOG.md                       # Version history
├── ARCHITECTURE.md                    # This file
├── COMPREHENSIVE_IMPROVEMENTS_SUMMARY.md # Improvement summary
├── SECOND_REVIEW_AFTER_IMPROVEMENTS.md  # Post-improvement review
└── START_HERE.txt                     # Quick start guide
```

---

## Core Components

### 1. Application Entry Points

#### `main.py` / `digital_signage_toolkit/main.py`
- **Purpose:** Application entry point
- **Responsibilities:**
  - Initialize PyQt6 application
  - Set application metadata (name, organization)
  - Create and display main window
  - Initialize logging system
  - Handle application lifecycle

#### `setup.py`
- **Purpose:** Python package installation configuration
- **Responsibilities:**
  - Define package metadata (name, version, author)
  - Specify dependencies (PyQt6, psutil)
  - Create console/gui script entry points
  - Package structure definition

---

### 2. GUI Layer (`gui/`)

#### `gui/main_window.py`
- **Purpose:** Main application window and UI orchestration
- **Responsibilities:**
  - Create and manage tabbed interface (6 tabs)
  - Handle user interactions and button clicks
  - Coordinate between GUI and business logic
  - Display status updates and activity logs
  - Manage worker threads for long-running operations
  - Show dialogs (password, confirmations, about)
  - Pre-flight validation checks

**Key Tabs:**
- **Master Setup:** Initial system configuration
- **Audit & Fix:** System maintenance and troubleshooting
- **OS Upgrade:** Operating system upgrades
- **Watchdog:** Rise Vision watchdog management
- **System Restore:** Timeshift snapshot management
- **Monitoring:** Hardware health and system status

#### `gui/widgets.py`
- **Purpose:** Custom reusable GUI widgets
- **Components:**
  - **LogConsole:** Real-time activity log display with color coding
  - **StatusWidget:** Status bar with color-coded messages

---

### 3. Core Business Logic (`core/`)

#### `core/system_ops.py`
- **Purpose:** System-level operations
- **Responsibilities:**
  - APT package management (update, upgrade, install, remove)
  - Hostname configuration
  - Display resolution management (X11/Wayland support)
  - Network connectivity checks
  - System reboot
  - APT configuration (auto-upgrades, sources.list backup/restore)
  - Display power management

#### `core/software_installer.py`
- **Purpose:** Third-party software installation
- **Responsibilities:**
  - TeamViewer installation (download, verify, install .deb)
  - Rise Vision Player installation (download, launch installer)
  - File downloads with retry, proxy, and bandwidth limiting
  - Checksum verification for downloaded files
  - Permission fixes (chrome-sandbox)
  - Cache clearing

#### `core/watchdog.py`
- **Purpose:** Rise Vision watchdog management
- **Responsibilities:**
  - Create watchdog script (checks if player is running)
  - Enable/disable cron-based watchdog
  - Configure automatic reboot schedules
  - Configure Rise Vision autostart
  - Atomic cron file operations (prevents race conditions)

#### `core/timeshift_manager.py`
- **Purpose:** System snapshot and restore management
- **Responsibilities:**
  - Install and configure Timeshift
  - Create system snapshots (before upgrades/fixes)
  - List available snapshots
  - Restore system from snapshot
  - Delete snapshots
  - Async snapshot operations (non-blocking)

#### `core/hardware_monitor.py`
- **Purpose:** Hardware health monitoring
- **Responsibilities:**
  - CPU usage monitoring
  - Memory usage statistics
  - Disk usage statistics
  - CPU temperature monitoring
  - TeamViewer status checking
  - System information gathering

---

### 4. Utility Modules (`utils/`)

#### `utils/config.py`
- **Purpose:** Configuration management with hierarchy
- **Responsibilities:**
  - Load configuration from user/system/default locations
  - Provide dot-notation access (e.g., `config.get('urls.teamviewer')`)
  - Path expansion (tilde, environment variables)
  - Configuration persistence
  - Default configuration values

**Configuration Hierarchy:**
1. User config: `~/.config/digital-signage-toolkit/config.json`
2. System config: `/etc/digital-signage-toolkit/config.json`
3. Default config: Built-in defaults

#### `utils/sudo_handler.py`
- **Purpose:** Sudo privilege management and security
- **Responsibilities:**
  - Check if sudo access is available
  - Request sudo password (GUI dialog or terminal)
  - Rate limiting (5 attempts per 5 minutes)
  - Keep sudo privileges alive (60-second refresh)
  - Execute commands with sudo
  - Async command execution
  - Password clearing from memory
  - Audit logging of privileged operations

#### `utils/validators.py`
- **Purpose:** Input validation and sanitization
- **Responsibilities:**
  - Hostname validation (RFC 1123 compliant)
  - Hostname sanitization
  - Snapshot ID validation (prevents shell injection)
  - Path validation (prevents directory traversal)
  - Resolution format validation
  - Path sanitization

#### `utils/logger.py`
- **Purpose:** Centralized logging and audit trail
- **Responsibilities:**
  - Application logging (general operations)
  - Audit logging (privileged operations with user/timestamp)
  - Error logging (exceptions with stack traces)
  - Log rotation (10MB files, 5 backups)
  - Fallback to user directory if system log dir unavailable
  - Security event logging

**Log Files:**
- `/var/log/digital-signage-toolkit/application.log`
- `/var/log/digital-signage-toolkit/audit.log`
- `/var/log/digital-signage-toolkit/error.log`

#### `utils/file_utils.py`
- **Purpose:** File operations and downloads
- **Responsibilities:**
  - SHA256 checksum calculation
  - File integrity verification
  - Download with retry logic (exponential backoff)
  - Proxy support (HTTP/HTTPS with authentication)
  - Bandwidth limiting
  - Timeout handling

#### `utils/preflight_checks.py`
- **Purpose:** Pre-installation validation
- **Responsibilities:**
  - Disk space validation
  - Python version checking
  - Internet connectivity checks
  - Required command availability
  - Sudo access verification
  - System resource monitoring (CPU, memory)

---

### 5. Deployment Scripts

#### `install-digital-signage-toolkit.sh`
- **Purpose:** Main installation script for Ubuntu
- **Responsibilities:**
  - Ubuntu version compatibility checking
  - Python version verification and installation
  - System dependency installation (apt packages)
  - Python package installation (pip with fallbacks)
  - Package structure creation
  - Launcher script creation
  - Desktop file creation and trust setting
  - Installation verification
  - Idempotent installation (can run multiple times)
  - Installation logging

#### `INSTALL_FROM_USB.sh`
- **Purpose:** Offline installation from USB drive
- **Responsibilities:**
  - Same as main installer but optimized for offline scenarios
  - Handles USB mount paths
  - Works without internet connection

#### `PREPARE_DEPLOYMENT.bat`
- **Purpose:** Windows batch script to prepare deployment package
- **Responsibilities:**
  - Create `deployment-ready` folder
  - Copy all necessary files
  - Create README with instructions
  - Open folder for easy access

#### `UNINSTALL.sh`
- **Purpose:** Clean uninstallation
- **Responsibilities:**
  - Remove application files
  - Remove desktop launcher
  - Remove configuration files
  - Clean up logs (optional)

#### `scripts/health_check.sh`
- **Purpose:** Post-deployment health verification
- **Responsibilities:**
  - Verify application installation
  - Check Python dependencies
  - Verify log directory permissions
  - Check disk space
  - Return exit code (0 = healthy)

---

### 6. Configuration Files

#### `config.json`
- **Purpose:** Default configuration template
- **Sections:**
  - `urls`: Download URLs for software
  - `checksums`: SHA256 checksums for verification
  - `paths`: File and directory paths
  - `watchdog`: Watchdog configuration
  - `reboot`: Automatic reboot settings
  - `display`: Display resolution settings
  - `timeshift`: Snapshot settings
  - `network`: Proxy, timeout, retry settings
  - `security`: Security settings (checksums, rate limiting)
  - `constants`: Timeout and interval constants

#### `requirements.txt`
- **Purpose:** Python package dependencies
- **Dependencies:**
  - PyQt6>=6.6.0 (GUI framework)
  - psutil>=5.9.0 (system monitoring)
  - pytest>=7.0.0 (testing, optional)
  - pytest-cov>=4.0.0 (coverage, optional)

#### `pytest.ini`
- **Purpose:** Pytest test configuration
- **Settings:**
  - Test discovery patterns
  - Output verbosity
  - Test paths

---

### 7. Debian Package Files (`debian/`)

#### `debian/control`
- Package metadata (name, version, description, dependencies)

#### `debian/rules`
- Build rules for creating .deb package

#### `debian/changelog`
- Package version history

#### `debian/logrotate.digital-signage-toolkit`
- Log rotation configuration (30-day retention, daily rotation)

---

### 8. Documentation

#### `README.md`
- Project overview, features, requirements, troubleshooting

#### `SETUP_INSTRUCTIONS.md`
- Step-by-step setup guide for technicians
- Network and USB deployment methods
- Usage instructions

#### `CHANGELOG.md`
- Version history and changes

#### `ARCHITECTURE.md`
- This file - project structure and architecture

---

## Architecture Patterns

### 1. Layered Architecture
```
GUI Layer (gui/)
    ↓
Business Logic Layer (core/)
    ↓
Utility Layer (utils/)
    ↓
System Layer (Linux/Ubuntu)
```

### 2. Separation of Concerns
- **GUI:** User interface and interaction
- **Core:** Business logic and system operations
- **Utils:** Reusable utilities and helpers
- **Config:** Centralized configuration management

### 3. Security Patterns
- **Input Validation:** All user inputs validated before use
- **Privilege Escalation:** Centralized sudo handler with rate limiting
- **Audit Trail:** All privileged operations logged
- **File Integrity:** Checksum verification for downloads

### 4. Error Handling
- **Try/Except Blocks:** All critical operations wrapped
- **Timeout Protection:** Long-running operations have timeouts
- **Graceful Degradation:** Application continues if non-critical operations fail
- **Error Logging:** All errors logged with context

### 5. Threading Model
- **WorkerThread:** Background operations (QThread-based)
- **Keep-Alive Thread:** Sudo privilege refresh (daemon thread)
- **Async Operations:** Snapshot creation/restore, software installation

---

## Data Flow

### Application Startup
1. `main.py` → Initialize logging
2. `main.py` → Create QApplication
3. `main_window.py` → Initialize UI components
4. `main_window.py` → Check sudo access
5. `main_window.py` → Run preflight checks
6. `main_window.py` → Start hardware monitoring

### User Operation Flow (Example: Master Setup)
1. User clicks "Start Master Setup"
2. `main_window.py` → Creates WorkerThread
3. WorkerThread → Calls operation function
4. Operation → Uses `system_ops.py` for system changes
5. Operation → Uses `software_installer.py` for software
6. Operation → Logs progress via logger
7. GUI → Updates progress bar and log console
8. Operation → Completes, updates status

### Download Flow
1. `software_installer.py` → Calls `file_utils.download_with_retry()`
2. `file_utils.py` → Checks config for proxy/bandwidth settings
3. `file_utils.py` → Downloads with retry logic
4. `file_utils.py` → Verifies checksum if provided
5. `software_installer.py` → Installs downloaded file
6. All steps → Logged to audit trail

---

## Key Design Decisions

### 1. Package Structure
- **Rationale:** Follows Python packaging best practices
- **Benefit:** Easy installation via pip, proper namespace

### 2. Configuration Hierarchy
- **Rationale:** Supports system-wide and user-specific settings
- **Benefit:** Flexible deployment scenarios

### 3. Centralized Sudo Handler
- **Rationale:** Single point for privilege management
- **Benefit:** Consistent security, audit trail, rate limiting

### 4. Worker Threads
- **Rationale:** Long operations would freeze GUI
- **Benefit:** Responsive UI, progress updates

### 5. Audit Logging
- **Rationale:** Compliance and security requirements
- **Benefit:** Complete audit trail of privileged operations

### 6. Input Validation
- **Rationale:** Prevent shell injection and security vulnerabilities
- **Benefit:** Secure command execution

### 7. Idempotent Installer
- **Rationale:** Safe to run multiple times
- **Benefit:** Easy updates, no manual cleanup needed

---

## Dependencies

### System Dependencies
- Ubuntu 18.04+ (or compatible Debian-based)
- Python 3.8+
- sudo access
- X11 or Wayland display server

### Python Dependencies
- **PyQt6:** GUI framework
- **psutil:** System monitoring
- **pytest:** Testing (development)

### External Tools Used
- `wget`: File downloads
- `apt-get`: Package management
- `xrandr`: Display resolution (X11)
- `timeshift`: System snapshots
- `sudo`: Privilege escalation
- `cron`: Scheduled tasks

---

## Security Architecture

### Authentication
- GUI password dialog for sudo access
- Rate limiting (5 attempts per 5 minutes)
- Password cleared from memory after use

### Authorization
- All privileged operations go through `SudoHandler`
- Centralized command execution
- Audit logging of all sudo operations

### Input Validation
- All user inputs validated before use
- Hostname, snapshot ID, paths, resolution validated
- Prevents shell injection attacks

### File Integrity
- SHA256 checksums for downloads
- Verification before installation
- Configurable (can be disabled if needed)

### Audit Trail
- All privileged operations logged
- User, timestamp, operation, status recorded
- Separate audit log file
- Log rotation and retention

---

## Deployment Architecture

### Windows → Ubuntu Deployment
1. **Windows:** Run `PREPARE_DEPLOYMENT.bat`
2. **Transfer:** Via TeamViewer or USB
3. **Ubuntu:** Run `install-digital-signage-toolkit.sh`
4. **Verification:** Run `health_check.sh`

### Installation Process
1. Pre-flight checks (disk space, Python version)
2. System dependency installation
3. Python package installation
4. Package structure creation
5. Launcher script creation
6. Desktop file creation
7. Verification

### Post-Installation
- Application accessible via desktop icon
- Command-line: `digital-signage-toolkit`
- Logs in `/var/log/digital-signage-toolkit/`
- Configuration in `~/.config/digital-signage-toolkit/`

---

## Testing Architecture

### Unit Tests
- **Location:** `tests/`
- **Framework:** pytest
- **Coverage:** Validators, file utilities
- **Run:** `pytest tests/`

### Test Structure
- `test_validators.py`: Input validation tests
- `test_file_utils.py`: File operation tests

### Future Testing
- Integration tests (full workflows)
- End-to-end tests
- Performance tests

---

## Logging Architecture

### Log Levels
- **INFO:** General operations
- **WARNING:** Non-critical issues
- **ERROR:** Errors and exceptions
- **AUDIT:** Privileged operations

### Log Files
- `application.log`: General application log
- `audit.log`: Audit trail (privileged operations)
- `error.log`: Error log (exceptions)

### Log Rotation
- **Size:** 10MB per file
- **Backups:** 5 files
- **Retention:** 30 days (via logrotate)
- **Compression:** After 1 day

---

## Configuration Architecture

### Configuration Sources (Priority Order)
1. User config: `~/.config/digital-signage-toolkit/config.json`
2. System config: `/etc/digital-signage-toolkit/config.json`
3. Default config: Built-in defaults

### Configuration Access
- Dot notation: `config.get('urls.teamviewer')`
- Path expansion: `config.expand_path('paths.player_dir')`
- Set values: `config.set('key.path', value)`

### Configuration Sections
- **urls:** Download URLs
- **checksums:** File integrity checksums
- **paths:** File and directory paths
- **network:** Proxy, timeout, retry settings
- **security:** Security settings
- **constants:** Timeout and interval values
- **watchdog:** Watchdog configuration
- **reboot:** Automatic reboot settings
- **display:** Display settings
- **timeshift:** Snapshot settings

---

## Extension Points

### Adding New Features
1. **Core Logic:** Add to `core/` directory
2. **GUI:** Add tab or widget in `gui/main_window.py`
3. **Configuration:** Add to `config.json` defaults
4. **Validation:** Add to `utils/validators.py` if needed
5. **Tests:** Add to `tests/` directory

### Adding New Software
1. Add download URL to `config.json`
2. Add checksum to `config.json` (optional)
3. Implement installation in `core/software_installer.py`
4. Add UI controls in `gui/main_window.py`

### Customization
- **Configuration:** Modify `config.json` or system config
- **UI:** Modify `gui/main_window.py` styles
- **Logging:** Modify `utils/logger.py` settings
- **Validation:** Modify `utils/validators.py` rules

---

## Maintenance

### Log Management
- Logs rotate automatically via logrotate
- Manual cleanup: `/var/log/digital-signage-toolkit/`
- User logs: `~/.local/log/digital-signage-toolkit/`

### Configuration Updates
- User config: `~/.config/digital-signage-toolkit/config.json`
- System config: `/etc/digital-signage-toolkit/config.json`
- Changes take effect on next application start

### Updates
- Run installer again (idempotent)
- Version checked before reinstall
- Existing configuration preserved

---

This architecture provides a robust, secure, and maintainable foundation for managing Ubuntu digital signage kiosks at scale.




