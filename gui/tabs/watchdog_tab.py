"""Watchdog tab for Digital Signage Toolkit."""
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSpinBox, QPushButton
)
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab


class WatchdogTab(BaseTab):
    """Watchdog Management tab for Rise Vision player control."""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.update_watchdog_status()
    
    def setup_ui(self):
        """Set up the Watchdog tab UI."""
        # Status section
        status_group = QGroupBox("Watchdog Status")
        status_layout = QVBoxLayout()
        
        self.watchdog_status_label = QLabel("Checking...")
        self.watchdog_status_label.setStyleSheet("padding: 10px; color: #f4f4f5;")
        status_layout.addWidget(self.watchdog_status_label)
        
        status_group.setLayout(status_layout)
        self.layout.addWidget(status_group)
        
        # Controls section
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        enable_btn = QPushButton("▶️ Enable Watchdog")
        enable_btn.setStyleSheet("background-color: #22c55e; color: white;")
        enable_btn.clicked.connect(self.enable_watchdog)
        controls_layout.addWidget(enable_btn)
        
        disable_btn = QPushButton("⏸️ Disable Watchdog")
        disable_btn.setStyleSheet("background-color: #eab308; color: white;")
        disable_btn.clicked.connect(self.disable_watchdog)
        controls_layout.addWidget(disable_btn)
        
        controls_group.setLayout(controls_layout)
        self.layout.addWidget(controls_group)
        
        # Reboot schedule section
        reboot_group = QGroupBox("Automatic Reboot Schedule")
        reboot_layout = QVBoxLayout()
        
        reboot_layout.addWidget(QLabel("Reboot Time:"))
        reboot_time_layout = QHBoxLayout()
        
        self.reboot_hour = QSpinBox()
        self.reboot_hour.setRange(0, 23)
        self.reboot_hour.setValue(3)
        reboot_time_layout.addWidget(self.reboot_hour)
        
        reboot_time_layout.addWidget(QLabel(":"))
        
        self.reboot_minute = QSpinBox()
        self.reboot_minute.setRange(0, 59)
        self.reboot_minute.setValue(0)
        reboot_time_layout.addWidget(self.reboot_minute)
        
        reboot_layout.addLayout(reboot_time_layout)
        
        schedule_btn = QPushButton("Set Reboot Schedule")
        schedule_btn.clicked.connect(self.set_reboot_schedule)
        reboot_layout.addWidget(schedule_btn)
        
        reboot_group.setLayout(reboot_layout)
        self.layout.addWidget(reboot_group)
        
        self.layout.addStretch()
    
    def update_watchdog_status(self):
        """Update watchdog status display."""
        status = self.watchdog_manager.get_service_status()
        if status.get('active', False) and status.get('enabled', False):
            self.watchdog_status_label.setText("Status: ▶️ ACTIVE (systemd)")
            self.watchdog_status_label.setStyleSheet("padding: 10px; color: #22c55e; font-weight: bold;")
        elif status.get('enabled', False):
            self.watchdog_status_label.setText("Status: ⚠️ ENABLED BUT INACTIVE")
            self.watchdog_status_label.setStyleSheet("padding: 10px; color: #eab308; font-weight: bold;")
        else:
            self.watchdog_status_label.setText("Status: ⏸️ PAUSED")
            self.watchdog_status_label.setStyleSheet("padding: 10px; color: #a1a1aa; font-weight: bold;")
    
    def enable_watchdog(self):
        """Enable watchdog."""
        if self.watchdog_manager.enable():
            self.log("Watchdog enabled", "SUCCESS")
            self.update_watchdog_status()
            self.set_status("Watchdog Enabled", "success")
        else:
            self.log("Failed to enable watchdog", "ERROR")
            self.set_status("Watchdog Enable Failed", "error")
    
    def disable_watchdog(self):
        """Disable watchdog."""
        if not self.confirm_action(
            "Disable Watchdog",
            "This will pause the watchdog and stop the Rise Vision player.\n\n"
            "Continue?"
        ):
            return
        
        if self.watchdog_manager.disable():
            self.watchdog_manager.stop_player()
            self.log("Watchdog disabled and player stopped", "SUCCESS")
            self.update_watchdog_status()
            self.set_status("Watchdog Disabled", "warning")
        else:
            self.log("Failed to disable watchdog", "ERROR")
    
    def set_reboot_schedule(self):
        """Set reboot schedule."""
        hour = self.reboot_hour.value()
        minute = self.reboot_minute.value()
        
        if self.watchdog_manager.configure_reboot_schedule(hour, minute):
            self.log(f"Reboot schedule set to {hour:02d}:{minute:02d}", "SUCCESS")
            self.set_status(f"Reboot scheduled for {hour:02d}:{minute:02d}", "success")
        else:
            self.log("Failed to set reboot schedule", "ERROR")
