"""Scheduler tab for Digital Signage Toolkit."""
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QCheckBox, QTimeEdit, QLabel, 
    QPushButton, QHBoxLayout
)
from PyQt6.QtCore import QTime, Qt
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab

class SchedulerTab(BaseTab):
    """Scheduler tab for managing automated tasks (Reboot, Shutdown, etc)."""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.load_schedule()
        
    def setup_ui(self):
        """Set up the Scheduler tab UI."""
        # 1. Scheduled Reboot
        reboot_group = QGroupBox("Daily Reboot (Memory Leak Prevention)")
        reboot_layout = QVBoxLayout()
        
        hint = QLabel("Scheduling a daily reboot helps prevent browser memory leaks.")
        hint.setStyleSheet("color: #a1a1aa; font-style: italic;")
        reboot_layout.addWidget(hint)
        
        self.reboot_check = QCheckBox("Enable Daily Reboot")
        self.reboot_check.toggled.connect(self._on_change)
        reboot_layout.addWidget(self.reboot_check)
        
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Reboot Time:"))
        
        self.reboot_time = QTimeEdit()
        self.reboot_time.setDisplayFormat("HH:mm")
        self.reboot_time.setTime(QTime(3, 0)) # Default 3 AM
        self.reboot_time.timeChanged.connect(self._on_change)
        time_layout.addWidget(self.reboot_time)
        time_layout.addStretch()
        
        reboot_layout.addLayout(time_layout)
        reboot_group.setLayout(reboot_layout)
        self.layout.addWidget(reboot_group)
        
        # 2. Power Schedule (Shutoff/Wake) -- Advanced
        # Note: Wake-on-LAN/RTC is hardware dependent. We will use 'rtcwake' or just shutdown.
        power_group = QGroupBox("Power Conservation Schedule")
        power_layout = QVBoxLayout()
        
        self.shutdown_check = QCheckBox("Enable Scheduled Shutdown (Save Power)")
        self.shutdown_check.toggled.connect(self._on_change)
        power_layout.addWidget(self.shutdown_check)
        
        shutdown_layout = QHBoxLayout()
        shutdown_layout.addWidget(QLabel("Shutdown Time:"))
        self.shutdown_time = QTimeEdit()
        self.shutdown_time.setDisplayFormat("HH:mm")
        self.shutdown_time.setTime(QTime(23, 0)) # Default 11 PM
        self.shutdown_time.timeChanged.connect(self._on_change)
        shutdown_layout.addWidget(self.shutdown_time)
        shutdown_layout.addStretch()
        
        power_layout.addLayout(shutdown_layout)
        
        # Warning about wake
        wake_warn = QLabel("Note: Systems must support BIOS Auto-Wake "
                           "or Wake-on-LAN to turn back on.")
        wake_warn.setStyleSheet("color: #eab308; font-size: 12px;")
        power_layout.addWidget(wake_warn)
        
        power_group.setLayout(power_layout)
        self.layout.addWidget(power_group)
        
        self.layout.addStretch()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("💾 Apply Schedule")
        self.apply_btn.setProperty("class", "primary")
        self.apply_btn.clicked.connect(self.apply_schedule)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_schedule)
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        
        self.layout.addLayout(btn_layout)
        
    def _on_change(self):
        """Enable apply button on change."""
        self.apply_btn.setEnabled(True)
        # In a real app we might style it to look "dirty"
        
    def load_schedule(self):
        """Load current cron schedule."""
        self.set_status("Loading schedule...", "working")
        
        def load_op():
            # In a real impl, we'd parse /etc/cron.d/dst-start or similar
            # Simulating load for now
            return {
                "reboot_enabled": False, # Default
                "reboot_time": "03:00",
                "shutdown_enabled": False
            }
            
        # We don't have a CronManager class yet, so we'll mock it or
        # use system_ops to read cron files in a future iteration.
        # For this Sprint, we'll focus on the UI and 'Apply' logic structure.
        self.set_status("Schedule loaded", "success")

    def apply_schedule(self):
        """Apply the schedule to the system (Cron)."""
        self.set_status("Applying schedule...", "working")
        
        reboot_enabled = self.reboot_check.isChecked()
        reboot_str = self.reboot_time.time().toString("HH:mm")
        
        shutdown_enabled = self.shutdown_check.isChecked()
        shutdown_str = self.shutdown_time.time().toString("HH:mm")
        
        def apply_op():
            try:
                # 1. Construct Cron Content
                cron_lines = []
                cron_lines.append("# Digital Signage Toolkit Schedule")
                cron_lines.append("SHELL=/bin/bash")
                cron_lines.append("PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin")
                
                if reboot_enabled:
                    h, m = reboot_str.split(':')
                    # format: m h dom mon dow user command
                    cron_lines.append(f"{m} {h} * * * root /sbin/reboot")
                    
                if shutdown_enabled:
                    h, m = shutdown_str.split(':')
                    cron_lines.append(f"{m} {h} * * * root /sbin/poweroff")
                    
                cron_content = "\n".join(cron_lines) + "\n"
                
                # 2. Write to tmp
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
                    tf.write(cron_content)
                    temp_path = tf.name
                    
                # 3. Move to /etc/cron.d/
                # Note: We need system_ops to have a 'install_cron' method ideally,
                # or just use run_command with mv
                result = self.main_window.sudo_handler.run_command(
                    ['mv', temp_path, '/etc/cron.d/dst-schedule'],
                    timeout=5
                )
                
                # Update permission
                self.main_window.sudo_handler.run_command(
                    ['chown', 'root:root', '/etc/cron.d/dst-schedule'], timeout=5
                )
                self.main_window.sudo_handler.run_command(
                    ['chmod', '644', '/etc/cron.d/dst-schedule'], timeout=5
                )
                
                if result.returncode == 0:
                    self.log(f"Schedule applied: Reboot={reboot_enabled} ({reboot_str})", "SUCCESS")
                    self.set_status("Schedule Applied", "success")
                else:
                    self.log(f"Failed to apply schedule: {result.stderr}", "ERROR")
                    self.set_status("Apply Failed", "error")
                    
            except Exception as e:
                self.log(f"Scheduler Error: {e}", "ERROR")
                self.set_status("Apply Failed", "error")
        
        self.start_worker(apply_op)
