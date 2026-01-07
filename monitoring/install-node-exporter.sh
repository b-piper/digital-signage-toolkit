#!/bin/bash
# ============================================================
# Node Exporter Installation Script
# ============================================================
# Run this on each kiosk to enable Prometheus monitoring
# Or use Ansible to deploy to all kiosks at once
#
# Usage:
#   chmod +x install-node-exporter.sh
#   sudo ./install-node-exporter.sh
# ============================================================

set -e

NODE_EXPORTER_VERSION="1.7.0"

echo "Installing Node Exporter v${NODE_EXPORTER_VERSION}..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Create user
useradd --system --no-create-home --shell /bin/false node_exporter 2>/dev/null || true

# Download and install
cd /tmp
wget -q "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar -xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/
chown node_exporter:node_exporter /usr/local/bin/node_exporter

# Clean up
rm -rf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64"*

# Create systemd service
cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
Documentation=https://prometheus.io/docs/guides/node-exporter/
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter \
    --collector.systemd \
    --collector.processes
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter

echo "Node Exporter installed and running on port 9100"
echo "Test: curl http://localhost:9100/metrics"
