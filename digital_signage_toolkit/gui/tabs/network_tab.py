"""Network Configuration tab."""
from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLineEdit,
    QMessageBox, QPushButton, QRadioButton
)
from .base_tab import BaseTab

class NetworkTab(BaseTab):
    """Tab to configure network settings with nmcli."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        
    def setup_ui(self):
        group = QGroupBox("Ubuntu Network Configuration")
        layout = QFormLayout()
        
        self.iface_edit = QLineEdit()
        self.iface_edit.setPlaceholderText("e.g. eth0, enp3s0")
        layout.addRow("Interface:", self.iface_edit)
        
        self.dhcp_radio = QRadioButton("DHCP")
        self.static_radio = QRadioButton("Static IP")
        self.dhcp_radio.setChecked(True)
        self.static_radio.toggled.connect(self.toggle_static_fields)
        
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.dhcp_radio)
        radio_layout.addWidget(self.static_radio)
        layout.addRow("Mode:", radio_layout)
        
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("192.168.1.50/24")
        self.gw_edit = QLineEdit()
        self.gw_edit.setPlaceholderText("192.168.1.1")
        self.dns_edit = QLineEdit()
        self.dns_edit.setPlaceholderText("8.8.8.8, 8.8.4.4")
        
        layout.addRow("IP Address/CIDR:", self.ip_edit)
        layout.addRow("Gateway:", self.gw_edit)
        layout.addRow("DNS Servers:", self.dns_edit)
        
        self.toggle_static_fields()
        group.setLayout(layout)
        self.layout.addWidget(group)
        
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("💾 Apply Settings (nmcli)")
        apply_btn.setProperty("class", "primary")
        apply_btn.setStyleSheet("background-color: #6366f1; color: white; padding: 10px; font-weight: bold;")
        apply_btn.clicked.connect(self.apply_network)
        btn_layout.addWidget(apply_btn)
        btn_layout.addStretch()
        
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def toggle_static_fields(self):
        """Enable or disable static IP fields based on radio selection."""
        is_static = self.static_radio.isChecked()
        self.ip_edit.setEnabled(is_static)
        self.gw_edit.setEnabled(is_static)
        self.dns_edit.setEnabled(is_static)

    def apply_network(self):
        """Apply network settings using NetworkManager."""
        iface = self.iface_edit.text().strip()
        if not iface:
            QMessageBox.warning(self, "Validation Error", "Interface name is required.")
            return

        self.set_status("Configuring network interface...", "working")
        self.log("Configuring network interface...", "COMMAND")

        def do_network():
            if self.dhcp_radio.isChecked():
                success = self.system_ops.configure_dhcp(iface)
            else:
                success = self.system_ops.configure_static_ip(
                    iface,
                    self.ip_edit.text().strip(),
                    self.gw_edit.text().strip(),
                    self.dns_edit.text().strip()
                )
            if success:
                self.log("Network configuration applied successfully", "SUCCESS")
                self.set_status("Network configured", "success")
            else:
                self.log("Failed to configure network", "ERROR")
                self.set_status("Network configuration failed", "error")
            return success

        self.start_worker(do_network)
