"""Settings/Configuration tab for Digital Signage Toolkit."""
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .base_tab import BaseTab


class ConfigTab(BaseTab):
    """Configuration UI tab for editing toolkit settings."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self._fields = {}
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """Set up the Settings/Configuration tab UI."""

        # --- URLs Section ---
        urls_group = QGroupBox("Download URLs")
        urls_layout = QFormLayout()

        self._fields['urls.teamviewer'] = QLineEdit()
        self._fields['urls.teamviewer'].setPlaceholderText("https://download.teamviewer.com/...")
        urls_layout.addRow("TeamViewer URL:", self._fields['urls.teamviewer'])

        self._fields['urls.rise_vision'] = QLineEdit()
        self._fields['urls.rise_vision'].setPlaceholderText("https://storage.googleapis.com/...")
        urls_layout.addRow("Rise Vision URL:", self._fields['urls.rise_vision'])

        urls_group.setLayout(urls_layout)
        self.layout.addWidget(urls_group)

        # --- Network Section ---
        network_group = QGroupBox("Network Settings")
        network_layout = QFormLayout()

        self._fields['network.proxy'] = QLineEdit()
        self._fields['network.proxy'].setPlaceholderText("http://proxy:3128 (leave empty for none)")
        network_layout.addRow("HTTP Proxy:", self._fields['network.proxy'])

        self._fields['network.timeout'] = QSpinBox()
        self._fields['network.timeout'].setRange(5, 300)
        self._fields['network.timeout'].setSuffix(" seconds")
        network_layout.addRow("Download Timeout:", self._fields['network.timeout'])

        self._fields['network.retry_attempts'] = QSpinBox()
        self._fields['network.retry_attempts'].setRange(0, 10)
        network_layout.addRow("Retry Attempts:", self._fields['network.retry_attempts'])

        self._fields['network.health_server_bind_address'] = QLineEdit()
        self._fields['network.health_server_bind_address'].setPlaceholderText("127.0.0.1")
        network_layout.addRow("Health Server Bind:", self._fields['network.health_server_bind_address'])

        network_group.setLayout(network_layout)
        self.layout.addWidget(network_group)

        # --- Fleet Configuration Section ---
        fleet_group = QGroupBox("Fleet Management")
        fleet_layout = QFormLayout()

        # Custom IP list manager
        ip_manager_widget = QWidget()
        ip_layout = QVBoxLayout(ip_manager_widget)
        ip_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ip_list = QListWidget()
        self.ip_list.setMaximumHeight(120)
        ip_layout.addWidget(self.ip_list)
        
        ip_controls = QHBoxLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g. 192.168.1.10")
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove Selected")
        
        ip_controls.addWidget(self.ip_input)
        ip_controls.addWidget(add_btn)
        ip_controls.addWidget(remove_btn)
        ip_layout.addLayout(ip_controls)
        
        def add_ip():
            ip = self.ip_input.text().strip()
            if ip:
                items = [self.ip_list.item(i).text() for i in range(self.ip_list.count())]
                if ip not in items:
                    self.ip_list.addItem(ip)
                self.ip_input.clear()
                
        def remove_ip():
            for item in self.ip_list.selectedItems():
                self.ip_list.takeItem(self.ip_list.row(item))
                
        add_btn.clicked.connect(add_ip)
        self.ip_input.returnPressed.connect(add_ip)
        remove_btn.clicked.connect(remove_ip)

        fleet_layout.addRow("Fleet IPs:", ip_manager_widget)

        fleet_group.setLayout(fleet_layout)
        self.layout.addWidget(fleet_group)

        # --- Monitoring Section ---
        monitoring_group = QGroupBox("Monitoring & Alerts")
        monitoring_layout = QFormLayout()

        self._fields['thermal.critical_threshold'] = QSpinBox()
        self._fields['thermal.critical_threshold'].setRange(50, 110)
        self._fields['thermal.critical_threshold'].setSuffix(" °C")
        monitoring_layout.addRow("Thermal Threshold:", self._fields['thermal.critical_threshold'])

        self._fields['security.api_token'] = QLineEdit()
        self._fields['security.api_token'].setPlaceholderText("API token for health endpoint")
        self._fields['security.api_token'].setEchoMode(QLineEdit.EchoMode.Password)
        monitoring_layout.addRow("Health API Token:", self._fields['security.api_token'])

        monitoring_group.setLayout(monitoring_layout)
        self.layout.addWidget(monitoring_group)

        # --- Timeshift Section ---
        timeshift_group = QGroupBox("System Restore")
        timeshift_layout = QFormLayout()

        self._fields['timeshift.snapshot_location'] = QLineEdit()
        self._fields['timeshift.snapshot_location'].setPlaceholderText("/timeshift")
        timeshift_layout.addRow("Snapshot Location:", self._fields['timeshift.snapshot_location'])

        timeshift_group.setLayout(timeshift_layout)
        self.layout.addWidget(timeshift_group)

        # --- Actions ---
        actions_layout = QHBoxLayout()

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setProperty("class", "primary")
        save_btn.setStyleSheet("background-color: #6366f1; color: white; padding: 10px 20px; font-weight: bold;")
        save_btn.clicked.connect(self.save_config)
        actions_layout.addWidget(save_btn)

        reload_btn = QPushButton("🔄 Reload")
        reload_btn.clicked.connect(self.load_config)
        actions_layout.addWidget(reload_btn)

        actions_layout.addStretch()

        self.layout.addLayout(actions_layout)

        # Info label
        info_label = QLabel(
            "Changes are saved to ~/.config/digital-signage-toolkit/config.json. "
            "Some changes may require a restart to take effect."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #71717a; font-size: 11px; padding: 8px;")
        self.layout.addWidget(info_label)

        self.layout.addStretch()

    def load_config(self):
        """Load current config values into UI fields."""
        config = self.main_window.config

        # Text fields
        for key in ['urls.teamviewer', 'urls.rise_vision', 'network.proxy',
                     'network.health_server_bind_address', 'timeshift.snapshot_location']:
            widget = self._fields.get(key)
            if widget and isinstance(widget, QLineEdit):
                widget.setText(str(config.get(key, '') or ''))

        # Fleet IPs list
        ip_str = str(config.get('fleet.ips', '') or '')
        self.ip_list.clear()
        for ip in ip_str.split(','):
            ip = ip.strip()
            if ip:
                self.ip_list.addItem(ip)

        # API token (special handling — may come from secrets manager)
        try:
            token = config.get('security.api_token', '')
            self._fields['security.api_token'].setText(str(token or ''))
        except Exception:
            self._fields['security.api_token'].setText('')

        # Spinbox fields
        spinbox_defaults = {
            'network.timeout': 30,
            'network.retry_attempts': 3,
            'thermal.critical_threshold': 85,
        }
        for key, default in spinbox_defaults.items():
            widget = self._fields.get(key)
            if widget and isinstance(widget, QSpinBox):
                val = config.get(key, default)
                try:
                    widget.setValue(int(val))
                except (ValueError, TypeError):
                    widget.setValue(default)

        self.log("Settings loaded", "INFO")
        self.set_status("Settings loaded", "info")

    def save_config(self):
        """Save UI field values back to config."""
        config = self.main_window.config

        # Text fields
        for key in ['urls.teamviewer', 'urls.rise_vision', 'network.proxy',
                     'network.health_server_bind_address', 'timeshift.snapshot_location']:
            widget = self._fields.get(key)
            if widget and isinstance(widget, QLineEdit):
                config.set(key, widget.text().strip())

        # Fleet IPs list
        ips = [self.ip_list.item(i).text() for i in range(self.ip_list.count())]
        config.set('fleet.ips', ','.join(ips))

        # API token
        token_text = self._fields['security.api_token'].text().strip()
        if token_text:
            config.set('security.api_token', token_text)

        # Spinbox fields
        for key in ['network.timeout', 'network.retry_attempts', 'thermal.critical_threshold']:
            widget = self._fields.get(key)
            if widget and isinstance(widget, QSpinBox):
                config.set(key, widget.value())

        try:
            config.save()
            self.log("Settings saved successfully", "SUCCESS")
            self.set_status("Settings saved", "success")
            QMessageBox.information(self, "Settings Saved",
                                    "Configuration has been saved.\n\n"
                                    "Some changes may require restarting the application.")
        except Exception as e:
            self.log(f"Failed to save settings: {e}", "ERROR")
            self.set_status("Save failed", "error")
            QMessageBox.critical(self, "Save Failed", f"Could not save configuration:\n{e}")
