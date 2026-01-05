# Digital Signage Toolkit

An Enterprise-Grade management utility for Rise Vision Player kiosks on Linux (Ubuntu). 

> **Goal**: Solve the "Ladder Problem" (Remote Management) and ensure 99.9% uptime for digital signage.

## Features

- **Ladder-Free Management**:
  - **Headless Mode**: check status via SSH (`dst-toolkit --status`).
  - **Remote Screenshots**: verify display content (`dst-toolkit --screenshot`).
  - **Email Alerts**: instant notification of service failures or disk issues.
- **Automated Health**:
  - **Daily Reboot**: prevents browser memory leaks via cron scheduler.
  - **Emergency Heal**: automated fix for permissions, cache corruption, and zombie processes.
  - **Process Watchdog**: deep inspection of `chrome`/`chromium` renderer processes.
- **Deployment**:
  - **Native `.deb` Package**: installs to `/opt` with dependency resolution.
  - **One-Line Installer**: `install.sh` for rapid deployment.

## Installation

### Option A: Debian Package (Recommended)
Building the package (requires Linux build machine):
```bash
./scripts/build_deb.sh 1.0.0
sudo apt install ./dst-toolkit_1.0.0_amd64.deb
```
This installs the app, dependencies, and creates the `dst-toolkit` command.

### Option B: Script Install
```bash
sudo bash scripts/install.sh
```

## Usage

### GUI Mode
Launch from the Applications menu or run:
```bash
dst-toolkit
```

### CLI / Headless Mode
For remote management via SSH:

```bash
# Get JSON status report (uptime, disk, service status)
dst-toolkit --status

# Output:
# {
#     "hostname": "kiosk-01",
#     "rise_player": { "service_active": true, "renderer_count": 4 },
#     "disk_free_gb": 12.5
# }

# Take a screenshot to verify content
dst-toolkit --screenshot /tmp/screen.png

# Run emergency repair (Clear cache, fix perms, restart)
dst-toolkit --heal
```

## Configuration

### SMTP Alerts
1. Open GUI -> **Alerts Tab**.
2. Configure SMTP Host (e.g., `smtp.office365.com`), Port (`587`), and Auth.
3. Click "Send Test Email".
4. Enable "Active Monitoring".

### Scheduling
1. Open GUI -> **Scheduler Tab**.
2. Set "Daily Reboot" time (Default: 03:00 AM).
3. Click "Apply". This updates `/etc/cron.d`.

## Development

- **Source**: `/opt/dst-toolkit` (Default install location)
- **Virtual Env**: `/opt/dst-toolkit/venv`
- **Logs**: `~/.dst-toolkit/logs/` (or via GUI Log Viewer)

### Project Structure
```
├── core/               # Backend logic (System Ops, Watchdog, Alerts)
├── gui/                # PyQt6 Reference Implementation
│   ├── tabs/           # Feature Tabs (Monitoring, Scheduler, Alerts)
│   └── themes.py       # "Zinc" Dark Theme definition
├── scripts/            # Build & Install scripts
└── main.py             # Entry point
```

## Maintenance

To uninstall:
```bash
sudo apt remove dst-toolkit
# or
sudo rm -rf /opt/dst-toolkit /usr/share/applications/dst-toolkit.desktop
```
