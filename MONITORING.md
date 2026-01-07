# Monitoring & Fleet Management Guide

This guide explains how to set up centralized monitoring for your Digital Signage kiosks.

## Quick Start (Phase A - No Server Required)

### Check Fleet Status

From any PC with network access to your kiosks:

```bash
# Edit scripts/check-fleet.sh with your kiosk IPs first
./scripts/check-fleet.sh
```

### Check Individual Kiosk

```bash
curl http://192.168.1.101:8080/health
```

---

## Full Monitoring Setup (Phase B - Requires Server)

### Prerequisites

- A Linux server/VM (Ubuntu 20.04+ recommended)
- Network access to all kiosks
- Ansible installed on your management PC

### Step 1: Install Prometheus & Grafana

On your monitoring server:

```bash
chmod +x monitoring/install-monitoring.sh
sudo ./monitoring/install-monitoring.sh
```

This installs:
- **Prometheus** on port 9090
- **Grafana** on port 3000

### Step 2: Configure Your Kiosks

Edit `/etc/prometheus/prometheus.yml` and add your kiosks:

```yaml
scrape_configs:
  - job_name: 'kiosks-node'
    static_configs:
      - targets:
        - '192.168.1.101:9100'  # kiosk-library
        - '192.168.1.102:9100'  # kiosk-cafeteria
        - '192.168.1.103:9100'  # kiosk-gym
        # Add all 20 kiosks...
```

Restart Prometheus:
```bash
sudo systemctl restart prometheus
```

### Step 3: Deploy Node Exporter to Kiosks

**Option A: Using Ansible (Recommended)**

1. Edit `monitoring/ansible/inventory/hosts.ini` with your kiosks
2. Run:
```bash
cd monitoring/ansible
ansible-playbook -i inventory/hosts.ini playbooks/deploy-node-exporter.yml
```

**Option B: Manual Installation**

On each kiosk:
```bash
chmod +x monitoring/install-node-exporter.sh
sudo ./monitoring/install-node-exporter.sh
```

### Step 4: Access Grafana Dashboard

1. Open http://YOUR_SERVER:3000
2. Login with admin/admin (change password)
3. Add Prometheus data source: http://localhost:9090
4. Import dashboard from `monitoring/grafana-dashboard.json`

---

## Ansible Playbooks

### Update All Kiosks
```bash
ansible-playbook -i inventory/hosts.ini playbooks/update-dst.yml
```

### Health Check All Kiosks
```bash
ansible-playbook -i inventory/hosts.ini playbooks/health-check.yml
```

### Reboot All Kiosks
```bash
ansible-playbook -i inventory/hosts.ini playbooks/reboot-all.yml
```

---

## Health Check API

Each kiosk exposes these endpoints on port 8080:

| Endpoint | Description |
|----------|-------------|
| `/health` | JSON health status |
| `/metrics` | Prometheus metrics |

### Example Response

```json
{
  "healthy": true,
  "hostname": "kiosk-library",
  "version": "2.1.4",
  "checks": {
    "rise_vision": {"running": true, "status": "running"},
    "disk": {"percent": 45.2, "critical": false},
    "memory": {"percent": 32.1, "critical": false}
  }
}
```

---

## Auto-Update

Kiosks automatically check for updates daily at 3:00 AM.

To force an update:
```bash
sudo /opt/dst-toolkit/scripts/auto-update.sh
```

Check update logs:
```bash
cat /var/log/dst-toolkit/auto-update.log
```
