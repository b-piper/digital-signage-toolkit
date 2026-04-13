"""Scheduler tab for Digital Signage Toolkit."""
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from digital_signage_toolkit.gui.widgets import StyledCheckBox
from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QTimeEdit, QVBoxLayout


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

        self.reboot_check = StyledCheckBox("Enable Daily Reboot")
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

        self.shutdown_check = StyledCheckBox("Enable Scheduled Shutdown (Save Power)")
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
        """Load current cron schedule from /etc/cron.d/dst-schedule."""
        self.set_status("Loading schedule...", "working")

        cron_path = "/etc/cron.d/dst-schedule"
        reboot_enabled = False
        reboot_time = "03:00"
        shutdown_enabled = False
        shutdown_time = "23:00"

        try:
            from pathlib import Path
            cron_file = Path(cron_path)
            if cron_file.exists():
                content = cron_file.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('SHELL') or line.startswith('PATH'):
                        continue
                    parts = line.split()
                    if len(parts) >= 7:
                        minute, hour = parts[0], parts[1]
                        command = ' '.join(parts[5:])
                        if '/sbin/reboot' in command:
                            reboot_enabled = True
                            reboot_time = f"{int(hour):02d}:{int(minute):02d}"
                        elif '/sbin/poweroff' in command:
                            shutdown_enabled = True
                            shutdown_time = f"{int(hour):02d}:{int(minute):02d}"
            else:
                # Also check the systemd reboot timer
                try:
                    result = self.main_window.sudo_handler.run_command(
                        ['systemctl', 'is-active', 'scc-reboot.timer'],
                        timeout=5
                    )
                    if result.returncode == 0:
                        reboot_enabled = True
                        import re
                        show_result = self.main_window.sudo_handler.run_command(
                            ['systemctl', 'show', 'scc-reboot.timer', '--property=TimersCalendar', '--no-pager'],
                            timeout=5
                        )
                        if show_result.returncode == 0 and show_result.stdout:
                            match = re.search(r'(\d{2}):(\d{2}):00', show_result.stdout)
                            if match:
                                reboot_time = f"{match.group(1)}:{match.group(2)}"
                except Exception:
                    pass
        except Exception as e:
            self.log(f"Could not read schedule: {e}", "WARNING")

        # Update UI
        self.reboot_check.setChecked(reboot_enabled)
        rh, rm = reboot_time.split(':')
        self.reboot_time.setTime(QTime(int(rh), int(rm)))

        self.shutdown_check.setChecked(shutdown_enabled)
        sh, sm = shutdown_time.split(':')
        self.shutdown_time.setTime(QTime(int(sh), int(sm)))

        self.apply_btn.setEnabled(False)
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
