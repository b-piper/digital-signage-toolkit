"""Alerts tab for Digital Signage Toolkit."""
import base64

from digital_signage_toolkit.core.alert_manager import AlertManager
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from digital_signage_toolkit.gui.widgets import StyledCheckBox
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout


class AlertsTab(BaseTab):
    """Tab for configuring email alerts."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.alert_manager = AlertManager(self.config_manager)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Set up the Alerts tab UI."""
        # 1. SMTP Settings
        smtp_group = QGroupBox("SMTP Server Configuration")
        smtp_layout = QVBoxLayout()

        self.enabled_check = StyledCheckBox("Enable Email Alerts")
        self.enabled_check.toggled.connect(self._on_change)
        smtp_layout.addWidget(self.enabled_check)

        # Grid for inputs
        grid_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("smtp.gmail.com")
        self.host_input.textChanged.connect(self._on_change)
        left_layout.addWidget(QLabel("SMTP Host:"))
        left_layout.addWidget(self.host_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(587)
        self.port_input.valueChanged.connect(self._on_change)
        right_layout.addWidget(QLabel("Port:"))
        right_layout.addWidget(self.port_input)

        grid_layout.addLayout(left_layout)
        grid_layout.addLayout(right_layout)
        smtp_layout.addLayout(grid_layout)

        # Auth
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("alerts@example.com")
        self.user_input.textChanged.connect(self._on_change)
        smtp_layout.addWidget(QLabel("Username / Email:"))
        smtp_layout.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("App Password")
        self.pass_input.textChanged.connect(self._on_change)
        smtp_layout.addWidget(QLabel("Password:"))
        smtp_layout.addWidget(self.pass_input)

        # Addresses
        addr_layout = QHBoxLayout()

        l_addr = QVBoxLayout()
        self.from_input = QLineEdit()
        self.from_input.textChanged.connect(self._on_change)
        l_addr.addWidget(QLabel("From Address:"))
        l_addr.addWidget(self.from_input)

        r_addr = QVBoxLayout()
        self.to_input = QLineEdit()
        self.to_input.textChanged.connect(self._on_change)
        r_addr.addWidget(QLabel("To Address:"))
        r_addr.addWidget(self.to_input)

        addr_layout.addLayout(l_addr)
        addr_layout.addLayout(r_addr)
        smtp_layout.addLayout(addr_layout)

        smtp_group.setLayout(smtp_layout)
        self.layout.addWidget(smtp_group)

        # Test & Save
        btn_layout = QHBoxLayout()

        self.test_btn = QPushButton("📧 Send Test Email")
        self.test_btn.clicked.connect(self.test_connection)

        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setProperty("class", "primary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_settings)

        btn_layout.addWidget(self.test_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)

        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def _on_change(self):
        self.save_btn.setEnabled(True)

    def load_settings(self):
        # Mock load from config
        # In real app: conf = self.config_manager.get("smtp", {})
        pass

    def save_settings(self):
        self.set_status("Saving settings...", "working")
        # Ensure config structure exists
        if "smtp" not in self.config_manager.config:
            self.config_manager.config["smtp"] = {}

        conf = self.config_manager.config["smtp"]
        conf["enabled"] = self.enabled_check.isChecked()
        conf["host"] = self.host_input.text()
        conf["port"] = self.port_input.value()
        conf["from_addr"] = self.from_input.text()
        conf["to_addr"] = self.to_input.text()

        # Handle password securely - obfuscate with base64
        if self.pass_input.text():
             raw_pass = self.pass_input.text()
             conf["password"] = base64.b64encode(raw_pass.encode()).decode()

        self.config_manager.save_config()
        self.set_status("Settings Saved", "success")
        self.save_btn.setEnabled(False)

    def test_connection(self):
        self.set_status("Testing SMTP...", "working")

        host = self.host_input.text()
        port = self.port_input.value()
        user = self.user_input.text()
        pwd = self.pass_input.text()
        f_addr = self.from_input.text()
        t_addr = self.to_input.text()

        def test_op():
            return self.alert_manager.test_connection(host, port, user, pwd, f_addr, t_addr)

        def on_complete(result):
            success, msg = result
            if success:
                self.log(f"SMTP Test: {msg}", "SUCCESS")
                self.set_status("Test Email Sent", "success")
            else:
                self.log(f"SMTP Error: {msg}", "ERROR")
                self.set_status("Test Failed", "error")

        # Manually run in worker since AlertManager is blocking
        # Note: BaseTab.start_worker expects a function that returns something
        self.start_worker(test_op, on_complete)
