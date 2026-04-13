# Digital Signage Toolkit

Enterprise-grade management utility for Rise Vision Player kiosks on Ubuntu Linux.

> **Goal**: Solve the "Ladder Problem" with remote management and ensure 99.9% uptime for digital signage.

[![CI](https://github.com/b-piper/digital-signage-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/b-piper/digital-signage-toolkit/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/b-piper/digital-signage-toolkit)](https://github.com/b-piper/digital-signage-toolkit/releases)

## Features

### Remote Management
- **Health Endpoint**: Each kiosk exposes `http://kiosk-ip:8080/health` for monitoring
- **Headless Mode**: Check status via SSH with `dst-toolkit --status`
- **Remote Screenshots**: Verify display content with `dst-toolkit --screenshot`
- **Fleet Management**: Ansible playbooks for bulk operations

### Automated Maintenance
- **Auto-Update**: Kiosks automatically update daily at 3 AM
- **Daily Reboot**: Prevents browser memory leaks via cron scheduler
- **Emergency Heal**: Automated fix for permissions, cache, and zombie processes
- **Process Watchdog**: Deep inspection of Chrome/Chromium renderer processes

### Monitoring & Alerting
- **Prometheus Metrics**: `/metrics` endpoint for Grafana integration
- **Email Alerts**: Automatic notification of service failures, disk issues, and thermal events
- **Fleet Status Script**: Quick overview of all kiosks from any PC

---

## Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
```

Or download the `.deb` from [Releases](https://github.com/b-piper/digital-signage-toolkit/releases):
```bash
sudo apt install ./dst-toolkit_X.X.X_amd64.deb
```

---

## Usage

### GUI Mode
Launch from Applications menu or:
```bash
dst-toolkit
```

### CLI / Headless Mode
```bash
# Get JSON status report
dst-toolkit --status

# Take a screenshot
dst-toolkit --screenshot /tmp/screen.png

# Run emergency repair
dst-toolkit --heal
```

### Health Check API
```bash
# Check kiosk health
curl http://kiosk-ip:8080/health

# Prometheus metrics
curl http://kiosk-ip:8080/metrics
```

---

## Fleet Management

See [MONITORING.md](MONITORING.md) for full details.

### Quick Fleet Check
```bash
./scripts/check-fleet.sh
```

### Using Ansible
```bash
cd monitoring/ansible

# Check health of all kiosks
ansible-playbook -i inventory/hosts.ini playbooks/health-check.yml

# Update DST on all kiosks
ansible-playbook -i inventory/hosts.ini playbooks/update-dst.yml

# Reboot all kiosks
ansible-playbook -i inventory/hosts.ini playbooks/reboot-all.yml
```

---

## GUI Navigation

The sidebar is organized into logical sections:

```
📊 Dashboard            ← Landing page with device state detection

INITIAL SETUP
  🚀 Master Setup       ← One-click provisioning for new machines
  ⬆️  OS Upgrade         ← Full Ubuntu release upgrades

MANAGEMENT
  🛡️ Watchdog            ← Rise Vision systemd service control
  📺 Rise Vision         ← Player start/stop, cache, reboot
  ⏰ Scheduler           ← Cron-based reboot/shutdown schedules
  🔔 Alerts              ← SMTP email notification config
  ⚙️  Settings            ← Edit toolkit configuration

DIAGNOSTICS
  📈 Monitoring          ← Live CPU/memory/disk/temp metrics
  📋 Logs                ← Application, audit, and system logs

MAINTENANCE
  💾 System Restore      ← Timeshift snapshot management
  🧹 Disk Cleanup        ← Reclaim disk space
```

---

## Configuration

### Settings Tab (GUI)
Open GUI → **Settings** to configure:
- Download URLs (TeamViewer, Rise Vision)
- Network settings (proxy, timeout, retry)
- Thermal alert threshold
- Health API token
- Timeshift snapshot location

### SMTP Alerts
1. Open GUI → **Alerts**
2. Configure SMTP Host, Port, and Auth
3. Click "Send Test Email"

### Scheduling
1. Open GUI → **Scheduler**
2. Set "Daily Reboot" time (Default: 03:00 AM)
3. Click "Apply"

### Disk Cleanup
Open GUI → **Disk Cleanup** to reclaim space:
- Clean APT cache
- Remove old kernels
- Trim journal logs
- Clean temporary files

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DST_CONFIG_PATH` | Custom config file location |
| `DST_SMTP_PASSWORD` | SMTP password (avoid storing in config) |
| `DST_SYSLOG_ENABLED` | Enable syslog forwarding |
| `DST_API_TOKEN` | Health endpoint auth token |

---

## Project Structure

```
├── core/               # Backend logic (System Ops, Watchdog, Alerts, Health)
├── gui/                # PyQt6 GUI
│   └── tabs/           # 12 feature tabs (Dashboard, Setup, Monitoring, etc.)
├── monitoring/         # Zabbix, Ansible fleet management
│   └── ansible/        # Inventory + 4 playbooks
├── scripts/            # Build, update, and fleet check scripts
└── main.py             # Entry point (GUI + CLI modes)
```

---

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Installation and release guide
- [MONITORING.md](MONITORING.md) - Fleet monitoring setup
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide

---

## Maintenance

### Uninstall
```bash
sudo apt remove dst-toolkit
```

### Logs
- Application: `/var/log/dst-toolkit/application.log`
- Auto-update: `/var/log/dst-toolkit/auto-update.log`
- User logs: `~/.dst-toolkit/logs/`

---

## License

Developed for Southwestern Community College IT Department.
