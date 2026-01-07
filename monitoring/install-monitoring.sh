#!/bin/bash
# ============================================================
# Digital Signage Toolkit - Monitoring Server Installation
# ============================================================
# This script installs Prometheus and Grafana on a management server
# Run this on your monitoring server (VM, PC, or Raspberry Pi)
#
# Requirements:
#   - Ubuntu 20.04+ or Debian 11+
#   - sudo access
#   - Internet connection
#
# Usage:
#   chmod +x install-monitoring.sh
#   sudo ./install-monitoring.sh
# ============================================================

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║     DIGITAL SIGNAGE TOOLKIT - MONITORING SERVER INSTALLATION         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install-monitoring.sh)"
    exit 1
fi

# ============================================================
# 1. Install Prometheus
# ============================================================
echo ""
echo "[1/4] Installing Prometheus..."

# Create Prometheus user
useradd --system --no-create-home --shell /bin/false prometheus 2>/dev/null || true

# Create directories
mkdir -p /etc/prometheus /var/lib/prometheus

# Download Prometheus
PROMETHEUS_VERSION="2.48.0"
cd /tmp
wget -q "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"
tar -xzf "prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"
cd "prometheus-${PROMETHEUS_VERSION}.linux-amd64"

# Install binaries
cp prometheus promtool /usr/local/bin/
cp -r consoles console_libraries /etc/prometheus/

# Set ownership
chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
chown prometheus:prometheus /usr/local/bin/{prometheus,promtool}

# Create systemd service
cat > /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus Monitoring System
Documentation=https://prometheus.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/var/lib/prometheus/ \
    --web.console.templates=/etc/prometheus/consoles \
    --web.console.libraries=/etc/prometheus/console_libraries \
    --web.listen-address=0.0.0.0:9090 \
    --web.enable-lifecycle
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "    Prometheus installed!"

# ============================================================
# 2. Configure Prometheus
# ============================================================
echo ""
echo "[2/4] Configuring Prometheus..."

# Check if config template exists
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
if [ -f "$SCRIPT_DIR/prometheus.yml.template" ]; then
    cp "$SCRIPT_DIR/prometheus.yml.template" /etc/prometheus/prometheus.yml
else
    # Create default config
    cat > /etc/prometheus/prometheus.yml << 'EOF'
# Prometheus configuration for Digital Signage Toolkit
# Edit this file to add your kiosks

global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files: []

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Digital Signage Kiosks
  # Add your kiosks here - each kiosk runs node_exporter on port 9100
  # and DST health server on port 8080
  - job_name: 'kiosks-node'
    static_configs:
      - targets:
        # Example: Replace with your actual kiosk IPs
        # - '192.168.1.101:9100'  # kiosk-library
        # - '192.168.1.102:9100'  # kiosk-cafeteria
        # - '192.168.1.103:9100'  # kiosk-gym
        - 'localhost:9100'  # Placeholder
    relabel_configs:
      - source_labels: [__address__]
        regex: '([^:]+):.*'
        target_label: instance
        replacement: '${1}'

  # DST Health Endpoints (custom metrics)
  - job_name: 'kiosks-dst'
    metrics_path: /metrics
    static_configs:
      - targets:
        # Example: Replace with your actual kiosk IPs
        # - '192.168.1.101:8080'  # kiosk-library
        # - '192.168.1.102:8080'  # kiosk-cafeteria
        # - '192.168.1.103:8080'  # kiosk-gym
        - 'localhost:8080'  # Placeholder
    relabel_configs:
      - source_labels: [__address__]
        regex: '([^:]+):.*'
        target_label: instance
        replacement: '${1}'
EOF
fi

chown prometheus:prometheus /etc/prometheus/prometheus.yml

echo "    Prometheus configured!"
echo "    IMPORTANT: Edit /etc/prometheus/prometheus.yml to add your kiosk IPs"

# ============================================================
# 3. Install Grafana
# ============================================================
echo ""
echo "[3/4] Installing Grafana..."

# Install dependencies
apt-get update -qq
apt-get install -y -qq apt-transport-https software-properties-common wget

# Add Grafana GPG key
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -

# Add Grafana repository
echo "deb https://packages.grafana.com/oss/deb stable main" > /etc/apt/sources.list.d/grafana.list

# Install Grafana
apt-get update -qq
apt-get install -y -qq grafana

echo "    Grafana installed!"

# ============================================================
# 4. Start Services
# ============================================================
echo ""
echo "[4/4] Starting services..."

systemctl daemon-reload
systemctl enable prometheus grafana-server
systemctl start prometheus grafana-server

echo "    Services started!"

# ============================================================
# Summary
# ============================================================
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    INSTALLATION COMPLETE!                            ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║                                                                      ║"
echo "║  Prometheus: http://${IP_ADDR}:9090                              ║"
echo "║  Grafana:    http://${IP_ADDR}:3000                              ║"
echo "║                                                                      ║"
echo "║  Grafana Login: admin / admin (change on first login)               ║"
echo "║                                                                      ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  NEXT STEPS:                                                         ║"
echo "║                                                                      ║"
echo "║  1. Edit /etc/prometheus/prometheus.yml                              ║"
echo "║     Add your kiosk IPs (e.g., 192.168.1.101:9100)                   ║"
echo "║                                                                      ║"
echo "║  2. Run the Ansible playbook to install node_exporter on kiosks:    ║"
echo "║     ansible-playbook monitoring/playbooks/deploy-monitoring.yml     ║"
echo "║                                                                      ║"
echo "║  3. Log into Grafana and import the DST dashboard:                  ║"
echo "║     - Go to Dashboards > Import                                      ║"
echo "║     - Upload monitoring/grafana-dashboard.json                       ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
