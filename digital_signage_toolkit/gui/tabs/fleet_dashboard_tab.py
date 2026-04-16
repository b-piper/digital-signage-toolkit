"""Fleet Dashboard tab for central monitoring of kiosks."""
import json
import urllib.request
import urllib.error
from PyQt6.QtWidgets import (
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget
)
from PyQt6.QtGui import QColor
from .base_tab import BaseTab
from ..main_window import WorkerThread

class FleetDashboardTab(BaseTab):
    """Dashboard for viewing multiple kiosk states."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        
    def setup_ui(self):
        # Header controls
        ctrl_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Fleet Status")
        refresh_btn.clicked.connect(self.refresh_fleet)
        refresh_btn.setStyleSheet("padding: 10px;")
        ctrl_layout.addWidget(refresh_btn)
        ctrl_layout.addStretch()
        self.layout.addLayout(ctrl_layout)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["IP Address", "Hostname", "Status", "Rise Vision"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.table)
        
        self.layout.addStretch()

    def refresh_fleet(self):
        """Fetch health from all listed IPs."""
        ips_str = self.main_window.config.get('fleet.ips', '')
        if not ips_str:
            self.log("No Fleet IPs configured. Go to Settings to add IPs.", "WARNING")
            return
            
        ips = [ip.strip() for ip in ips_str.split(',') if ip.strip()]
        self.table.setRowCount(0)
        self.log(f"Polling {len(ips)} endpoints...", "INFO")
        
        def worker_poll(ip_list, token):
            results = []
            for ip in ip_list:
                req = urllib.request.Request(f"http://{ip}:8080/health")
                if token:
                    req.add_header("X-Auth-Token", token)
                try:
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read().decode())
                        results.append({"ip": ip, "data": data, "error": None})
                except Exception as e:
                    results.append({"ip": ip, "data": None, "error": str(e)})
            return results
            
        token = self.main_window.config.get('security.api_token', '')
        self.worker = WorkerThread(worker_poll, ips, token)
        self.worker.result_signal.connect(self.populate_table)
        self.worker.start()

    def populate_table(self, results):
        """Populate table with poll results."""
        self.table.setRowCount(len(results))
        for row, res in enumerate(results):
            ip = res["ip"]
            data = res["data"]
            
            ip_item = QTableWidgetItem(ip)
            self.table.setItem(row, 0, ip_item)
            
            if data:
                host_item = QTableWidgetItem(data.get("hostname", "Unknown"))
                
                status_item = QTableWidgetItem("Healthy" if data.get("healthy") else "Unhealthy")
                status_item.setForeground(QColor("green") if data.get("healthy") else QColor("red"))
                
                rv = data.get("checks", {}).get("rise_vision", {})
                rv_item = QTableWidgetItem("Running" if rv.get("running") else "Stopped")
                if not rv.get("running"):
                    rv_item.setForeground(QColor("red"))
                
                self.table.setItem(row, 1, host_item)
                self.table.setItem(row, 2, status_item)
                self.table.setItem(row, 3, rv_item)
            else:
                self.table.setItem(row, 1, QTableWidgetItem("Offline"))
                err_item = QTableWidgetItem(f"Error ({res['error']})")
                err_item.setForeground(QColor("red"))
                self.table.setItem(row, 2, err_item)
                self.table.setItem(row, 3, QTableWidgetItem("-"))
        
        self.log("Fleet poll complete.", "SUCCESS")
