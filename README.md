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
- **Email Alerts**: Instant notification of service failures or disk issues
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

## Configuration

### SMTP Alerts
1. Open GUI → **Alerts Tab**
2. Configure SMTP Host, Port, and Auth
3. Click "Send Test Email"
4. Enable "Active Monitoring"

### Scheduling
1. Open GUI → **Scheduler Tab**
2. Set "Daily Reboot" time (Default: 03:00 AM)
3. Click "Apply"

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DST_CONFIG_PATH` | Custom config file location |
| `DST_SMTP_PASSWORD` | SMTP password (avoid storing in config) |
| `DST_SYSLOG_ENABLED` | Enable syslog forwarding |

---

## Project Structure

```
├── core/               # Backend logic (System Ops, Watchdog, Alerts)
├── gui/                # PyQt6 GUI
│   └── tabs/           # Feature Tabs (Monitoring, Scheduler, Alerts)
├── monitoring/         # Prometheus, Grafana, Ansible setup
│   └── ansible/        # Fleet management playbooks
├── scripts/            # Build & maintenance scripts
└── main.py             # Entry point
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
