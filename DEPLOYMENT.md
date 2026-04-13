# Deployment Guide

## Quick Install (Recommended)

Download **`install.sh`** from the [latest release](https://github.com/b-piper/digital-signage-toolkit/releases/latest). This is a self-extracting installer — the `.deb` package is embedded inside it. **No other files needed.**

1. Copy `install.sh` to the kiosk (USB drive, network share, etc.)
2. Right-click → Properties → "Allow Executing as Program"
3. Double-click to run (enter password when prompted)

Or from a terminal:
```bash
sudo bash install.sh
```

## Alternative Install Methods

### Remote one-liner (requires internet)
```bash
curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
```

### Standalone .deb (advanced)
Download from [Releases](https://github.com/b-piper/digital-signage-toolkit/releases):
```bash
sudo apt install ./dst-toolkit_X.X.X_amd64.deb
```

---

## Auto-Update

Kiosks automatically check for updates **daily at 3:00 AM**.

To check auto-update status:
```bash
systemctl status dst-auto-update.timer
```

To force an immediate update:
```bash
sudo /opt/dst-toolkit/scripts/auto-update.sh
```

View update logs:
```bash
cat /var/log/dst-toolkit/auto-update.log
```

---

## Creating a Release

1. Commit your changes:
   ```bash
   git add . && git commit -m "Your changes"
   ```

2. Tag the release:
   ```bash
   git tag v2.2.0
   ```

3. Push with tags:
   ```bash
   git push origin main --tags
   ```

GitHub Actions automatically builds and publishes the `.deb` package.

---

## Bulk Update (All Kiosks)

### Using Ansible (Recommended)
```bash
cd monitoring/ansible
ansible-playbook -i inventory/hosts.ini playbooks/update-dst.yml
```

### Manual SSH Loop
```bash
for ip in 192.168.1.{101..120}; do
    ssh rise@$ip "curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash"
done
```

---

## Network Setup (Cisco Meraki)

For DHCP environments, use **DHCP reservations** so kiosks get consistent IPs:

1. Go to Meraki Dashboard → **Network-wide** → **Clients**
2. Find each kiosk and note its MAC address
3. Go to **Security & SD-WAN** → **Addressing & VLANs**
4. Add **Fixed IP assignment** for each kiosk
5. Update `monitoring/ansible/inventory/hosts.ini` with the reserved IPs

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DST_CONFIG_PATH` | Custom config file location |
| `DST_SMTP_PASSWORD` | SMTP password (avoid storing in config) |
| `DST_SYSLOG_ENABLED` | Enable syslog forwarding (`true`/`false`) |
| `DST_SYSLOG_ADDRESS` | Syslog address (default: `/dev/log`) |

---

## Verifying Installation

After install, verify the toolkit is working:

```bash
# Check service
dst-toolkit --status

# Check health endpoint
curl http://localhost:8080/health

# Check auto-update timer
systemctl status dst-auto-update.timer

# Check version
cat /opt/dst-toolkit/VERSION
```
