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
│   ├── main_window.py                 # Main window with grouped sidebar navigation
│   ├── widgets.py                     # Custom GUI widgets (LogConsole, StatusWidget)
│   ├── transitions.py                 # FadeStackedWidget for page transitions
│   ├── themes.py                      # Theme/styling definitions
│   ├── dialogs.py                     # Modal dialogs (About, etc.)
│   └── tabs/                          # Feature tabs (one per file)
│       ├── __init__.py                # Tab exports
│       ├── base_tab.py                # Base class for all tabs
│       ├── dashboard_tab.py           # Dashboard with device state detection
│       ├── master_setup_tab.py        # Initial system provisioning
│       ├── os_upgrade_tab.py          # OS release upgrades
│       ├── watchdog_tab.py            # Rise Vision watchdog management
│       ├── rise_vision_tab.py         # Rise Vision player operations
│       ├── scheduler_tab.py           # Cron-based reboot/shutdown schedules
│       ├── alerts_tab.py              # SMTP email alert configuration
│       ├── config_tab.py              # Settings/configuration UI
│       ├── monitoring_tab.py          # Live hardware health metrics
│       ├── log_viewer_tab.py          # Application and system logs
│       ├── restore_tab.py             # Timeshift snapshot management
│       └── disk_cleanup_tab.py        # Disk maintenance operations
│
├── core/                              # Core business logic
│   ├── __init__.py
│   ├── system_ops.py                  # System operations (apt, hostname, display)
│   ├── software_installer.py          # Software installation (TeamViewer, Rise Vision)
│   ├── watchdog.py                    # Watchdog management (systemd service)
│   ├── timeshift_manager.py           # System snapshot/restore management
│   ├── hardware_monitor.py            # Hardware health monitoring
│   ├── alert_manager.py               # SMTP email alerts with cooldown
│   └── health_server.py               # HTTP health + Prometheus metrics endpoints
│
├── utils/                             # Utility modules
│   ├── __init__.py
│   ├── config.py                      # Configuration management (hierarchical)
│   ├── sudo_handler.py                # Sudo privilege management
│   ├── validators.py                  # Input validation and sanitization
│   ├── logger.py                      # Centralized logging and audit trail
│   ├── file_utils.py                  # File operations (downloads, checksums)
│   ├── secrets_manager.py             # Secure credential storage
│   ├── error_handling.py              # Error decorator patterns
│   └── preflight_checks.py            # Pre-installation validation
│
├── tests/                             # Unit tests (13 test files)
│   ├── conftest.py                    # Pytest fixtures
│   ├── test_config.py
│   ├── test_error_handling.py
│   ├── test_file_utils.py
│   ├── test_hardware_monitor.py
│   ├── test_preflight_checks.py
│   ├── test_secrets_manager.py
│   ├── test_software_installer.py
│   ├── test_sudo_handler.py
│   ├── test_system_ops.py
│   ├── test_timeshift_manager.py
│   ├── test_validators.py
│   └── test_watchdog.py
│
├── monitoring/                        # Fleet management
│   └── ansible/
│       ├── inventory/
│       │   └── hosts.ini              # Kiosk inventory
│       └── playbooks/
│           ├── health-check.yml       # Query health on all kiosks
│           ├── update-dst.yml         # Update toolkit on all kiosks
│           ├── reboot-all.yml         # Scheduled fleet reboot
│           └── deploy-zabbix.yml      # Deploy Zabbix agent
│
├── scripts/                           # Deployment and utility scripts
│   ├── auto-update.sh                 # Daily auto-update via GitHub releases
│   ├── build_deb.sh                   # Build .deb package
│   └── check-fleet.sh                # Fleet health status check
│
├── debian/                            # Debian package configuration
│   ├── changelog
│   ├── compat
│   ├── control
│   ├── rules
│   ├── digital-signage-toolkit.desktop
│   ├── digital-signage-toolkit.png
│   └── logrotate.digital-signage-toolkit
│
├── main.py                            # Root-level entry point
├── install-remote.sh                  # One-line remote installer
├── setup.py                           # Python package setup
├── requirements.txt                   # Python dependencies
├── config.json                        # Default configuration
├── pytest.ini                         # Pytest configuration
│
├── README.md                          # Project overview and features
├── DEPLOYMENT.md                      # Installation and release guide
├── MONITORING.md                      # Fleet monitoring (Zabbix) setup
├── ARCHITECTURE.md                    # This file
└── CONTRIBUTING.md                    # Development guide
```

---

## GUI Architecture

### Sidebar Navigation (Grouped)

The main window uses a `QListWidget` sidebar with non-clickable section headers dividing tabs into logical groups:

```
📊 Dashboard              ← Device state detection, status cards, recommendations

── INITIAL SETUP ──
🚀 Master Setup            ← One-click provisioning (hostname, software, watchdog)
⬆️  OS Upgrade              ← Full Ubuntu release upgrade with snapshot

── MANAGEMENT ──
🛡️ Watchdog                ← systemd service control + deep inspection
📺 Rise Vision             ← Player start/stop/restart, cache, reboot
⏰ Scheduler               ← Cron-based reboot/shutdown schedules
🔔 Alerts                  ← SMTP email configuration
⚙️  Settings                ← GUI config editor (URLs, network, thresholds)

── DIAGNOSTICS ──
📈 Monitoring              ← CPU/memory/disk/temp, display management
📋 Logs                    ← Application, audit, error, and journalctl logs

── MAINTENANCE ──
💾 System Restore          ← Timeshift snapshot CRUD
🧹 Disk Cleanup            ← APT cache, old kernels, journal, /tmp
```

Section headers are implemented as `QListWidgetItem` with `Qt.ItemFlag.NoItemFlags` to prevent selection. A `_row_to_page` mapping dictionary translates sidebar row indices to `QStackedWidget` page indices, skipping header rows.

### Tab Architecture

All tabs inherit from `BaseTab(QWidget)` which provides:
- Thread-safe logging via `log_signal`
- Thread-safe status updates via `status_signal`
- Access to shared resources via properties (`config`, `sudo_handler`, `system_ops`, etc.)
- Worker thread creation via `start_worker()`
- Confirmation/warning/error dialogs

---

## Core Components

### 1. System Operations (`core/system_ops.py`)
- APT package management (update, upgrade, install, remove)
- Hostname configuration
- Display resolution management (X11 via `xrandr` + Wayland via `wlr-randr`)
- Network connectivity checks, ping latency
- System reboot with cache clearing
- Rise Vision player status (deep inspection: renderer count, memory)
- Screen wake, screenshots

### 2. Software Installer (`core/software_installer.py`)
- TeamViewer installation (download, verify checksum, install .deb)
- Rise Vision Player installation (synchronous, display-aware)
- Download with retry, proxy support, and bandwidth limiting
- Cache clearing

### 3. Watchdog Manager (`core/watchdog.py`)
- Creates/manages systemd service for Rise Vision
- Enable/disable/status with deep inspection
- Reboot schedule via systemd timer
- Autostart configuration
- Atomic cron file operations

### 4. Health Server (`core/health_server.py`)
- `/health` endpoint returning JSON health status
- `/metrics` endpoint returning Prometheus text exposition format
- Token-based authentication (`X-Auth-Token` header)
- Localhost-bound by default (configurable)
- Auto-triggers email alerts when unhealthy (with 10-minute cooldown)

### 5. Alert Manager (`core/alert_manager.py`)
- SMTP email sending with TLS support
- Cooldown mechanism to prevent alert spam
- Password retrieval: env var → keyring → config hierarchy
- Automatically triggered by health server and monitoring tab on critical events

### 6. Timeshift Manager (`core/timeshift_manager.py`)
- System snapshot CRUD operations
- Auto-snapshot before upgrades/fixes
- Async snapshot creation with callbacks

### 7. Hardware Monitor (`core/hardware_monitor.py`)
- CPU usage, memory, disk, temperature monitoring
- Thermal critical detection with configurable threshold
- TeamViewer status checking

---

## Security Architecture

### Authentication & Authorization
- All privileged operations go through `SudoHandler` with rate limiting (5 attempts/5 min)
- Health API requires `X-Auth-Token` header when `security.require_auth` is enabled
- Password cleared from memory after use
- Application enforces root execution via `pkexec`

### Input Validation
- All user inputs validated via `utils/validators.py`
- Hostname (RFC 1123), snapshot IDs, paths, resolutions validated
- Prevents shell injection attacks

### Audit Trail
- All privileged operations logged to `audit.log`
- Separate application, audit, and error log files
- Log rotation: 10MB per file, 5 backups, 30-day retention via logrotate

### File Integrity
- SHA256 checksum verification for downloads
- `.deb` package validation before installation
- `NoNewPrivileges` in systemd service unit

---

## Configuration Architecture

### Sources (Priority Order)
1. CLI-specified: `DST_CONFIG_PATH` environment variable
2. User config: `~/.config/digital-signage-toolkit/config.json`
3. System config: `/etc/digital-signage-toolkit/config.json`
4. Built-in defaults

### Access Pattern
- Dot notation: `config.get('urls.teamviewer')`
- Path expansion: `config.expand_path('paths.player_dir')`
- Sensitive values routed through `SecretsManager`
- File locking via `fcntl.flock()` for concurrent access

### GUI Configuration
The Settings tab (`config_tab.py`) provides a form-based UI for editing key configuration values. Changes are saved to the user config file via `Config.set()` + `Config.save()`.

---

## Deployment Architecture

### Installation Methods
1. **Remote (one-liner)**: `curl -sSL .../install-remote.sh | sudo bash`
2. **Manual .deb**: `sudo apt install ./dst-toolkit_X.X.X_amd64.deb`
3. **Fleet (Ansible)**: `ansible-playbook playbooks/update-dst.yml`

### Auto-Update
- systemd timer runs `auto-update.sh` daily at 3 AM
- Checks GitHub releases for new `.deb`
- Validates package before installation
- Automatic rollback on failure
- Keeps 3 most recent backups

### Fleet Management
- Ansible inventory in `monitoring/ansible/inventory/hosts.ini`
- 4 playbooks: health-check, update, reboot, deploy-zabbix
- `scripts/check-fleet.sh` for quick terminal-based fleet overview

---

## Threading Model

- **WorkerThread (QThread)**: Background operations with signal-based UI updates
- **Keep-Alive Thread**: Sudo credential refresh (60-second daemon)
- **Health Server**: Background `HTTPServer` in daemon thread
- **Hardware Monitor**: QTimer-based polling (5-second interval)

---

## Dependencies

### System
- Ubuntu 18.04+ (or compatible Debian-based)
- Python 3.8+
- sudo access
- X11 or Wayland display server

### Python
- PyQt6 >= 6.6.0 (GUI framework)
- psutil >= 5.9.0 (system monitoring)
- qtawesome (icon library)
- pytest >= 7.0.0 (testing)

### External Tools
- `wget`, `curl`: File downloads
- `apt-get`: Package management
- `xrandr` / `wlr-randr`: Display resolution
- `timeshift`: System snapshots
- `scrot`: Screenshots

---

This architecture provides a robust, secure, and maintainable foundation for managing Ubuntu digital signage kiosks at scale.
