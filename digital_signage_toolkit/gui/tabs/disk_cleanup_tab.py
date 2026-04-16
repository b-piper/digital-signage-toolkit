"""Disk Cleanup tab for Digital Signage Toolkit."""
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .base_tab import BaseTab


class DiskCleanupTab(BaseTab):
    """Tab for disk cleanup and maintenance operations."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.refresh_disk_info()

    def setup_ui(self):
        """Set up the Disk Cleanup tab UI."""

        # --- Disk Usage Overview ---
        usage_group = QGroupBox("Disk Usage")
        usage_layout = QVBoxLayout()

        self.disk_info_label = QLabel("Checking...")
        self.disk_info_label.setStyleSheet(
            "font-family: monospace; padding: 12px; color: #e0e0e0; "
            "background-color: #27272a; border: 1px solid #3f3f46; border-radius: 6px;"
        )
        usage_layout.addWidget(self.disk_info_label)

        refresh_btn = QPushButton("🔄 Refresh Disk Info")
        refresh_btn.clicked.connect(self.refresh_disk_info)
        usage_layout.addWidget(refresh_btn)

        usage_group.setLayout(usage_layout)
        self.layout.addWidget(usage_group)

        # --- Cleanup Actions ---
        cleanup_group = QGroupBox("Cleanup Actions")
        cleanup_layout = QVBoxLayout()

        # APT cache cleanup
        apt_row = QHBoxLayout()
        apt_label = QLabel("APT Package Cache")
        apt_label.setStyleSheet("color: #e0e0e0;")
        apt_label.setToolTip("Clear downloaded .deb files from the apt cache")
        apt_row.addWidget(apt_label)
        apt_row.addStretch()
        self.apt_size_label = QLabel("")
        self.apt_size_label.setStyleSheet("color: #a1a1aa;")
        apt_row.addWidget(self.apt_size_label)
        apt_btn = QPushButton("🧹 Clean APT Cache")
        apt_btn.clicked.connect(self.clean_apt_cache)
        apt_row.addWidget(apt_btn)
        cleanup_layout.addLayout(apt_row)

        # Old kernels
        kernel_row = QHBoxLayout()
        kernel_label = QLabel("Old Kernels")
        kernel_label.setStyleSheet("color: #e0e0e0;")
        kernel_label.setToolTip("Remove old kernel packages that are no longer needed")
        kernel_row.addWidget(kernel_label)
        kernel_row.addStretch()
        self.kernel_info_label = QLabel("")
        self.kernel_info_label.setStyleSheet("color: #a1a1aa;")
        kernel_row.addWidget(self.kernel_info_label)
        kernel_btn = QPushButton("🧹 Remove Old Kernels")
        kernel_btn.clicked.connect(self.remove_old_kernels)
        kernel_row.addWidget(kernel_btn)
        cleanup_layout.addLayout(kernel_row)

        # Journal logs
        journal_row = QHBoxLayout()
        journal_label = QLabel("System Journal Logs")
        journal_label.setStyleSheet("color: #e0e0e0;")
        journal_label.setToolTip("Trim systemd journal logs older than 7 days")
        journal_row.addWidget(journal_label)
        journal_row.addStretch()
        self.journal_size_label = QLabel("")
        self.journal_size_label.setStyleSheet("color: #a1a1aa;")
        journal_row.addWidget(self.journal_size_label)
        journal_btn = QPushButton("🧹 Trim Journal Logs")
        journal_btn.clicked.connect(self.trim_journal_logs)
        journal_row.addWidget(journal_btn)
        cleanup_layout.addLayout(journal_row)

        # Tmp files
        tmp_row = QHBoxLayout()
        tmp_label = QLabel("Temporary Files")
        tmp_label.setStyleSheet("color: #e0e0e0;")
        tmp_label.setToolTip("Clean old temporary files from /tmp")
        tmp_row.addWidget(tmp_label)
        tmp_row.addStretch()
        tmp_btn = QPushButton("🧹 Clean /tmp")
        tmp_btn.clicked.connect(self.clean_tmp)
        tmp_row.addWidget(tmp_btn)
        cleanup_layout.addLayout(tmp_row)

        cleanup_group.setLayout(cleanup_layout)
        self.layout.addWidget(cleanup_group)

        # Full cleanup button
        full_btn = QPushButton("🧹 Run Full Cleanup")
        full_btn.setProperty("class", "primary")
        full_btn.setStyleSheet(
            "background-color: #6366f1; color: white; padding: 12px; "
            "font-weight: bold; font-size: 13px;"
        )
        full_btn.setToolTip("Run all cleanup operations at once")
        full_btn.clicked.connect(self.run_full_cleanup)
        self.layout.addWidget(full_btn)

        # Info
        info_label = QLabel(
            "💡 Tip: Regular disk cleanup prevents the kiosk from running out of space, "
            "which can cause Rise Vision to stop displaying content."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "padding: 12px; background-color: #27272a; border-radius: 6px; "
            "color: #a1a1aa; font-size: 12px;"
        )
        self.layout.addWidget(info_label)

        self.layout.addStretch()

    def refresh_disk_info(self):
        """Refresh disk usage information."""
        try:
            disk = self.hardware_monitor.get_disk_usage()
            pct = disk.get('percent', 0)
            used = disk.get('used_gb', 0)
            total = disk.get('total_gb', 0)
            free = total - used

            color = "#ef4444" if pct > 90 else "#eab308" if pct > 80 else "#22c55e"

            text = f"<span style='color:{color}; font-size:18px; font-weight:bold'>{pct:.1f}% Used</span><br><br>"
            text += f"<span style='color:#a1a1aa'>Used:</span> {used:.1f} GB<br>"
            text += f"<span style='color:#a1a1aa'>Free:</span> {free:.1f} GB<br>"
            text += f"<span style='color:#a1a1aa'>Total:</span> {total:.1f} GB"
            self.disk_info_label.setText(text)

            # Try to get apt cache size
            try:
                import subprocess
                result = subprocess.run(
                    ['du', '-sh', '/var/cache/apt/archives'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    size = result.stdout.split()[0]
                    self.apt_size_label.setText(f"({size})")
            except Exception:
                self.apt_size_label.setText("")

            # Try to get journal size
            try:
                import subprocess
                result = subprocess.run(
                    ['journalctl', '--disk-usage'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    # Output like "Archived and active journals take up 120.0M in the file system."
                    parts = result.stdout.strip()
                    self.journal_size_label.setText(f"({parts.split('take up ')[-1].split(' in')[0]})" if 'take up' in parts else "")
            except Exception:
                self.journal_size_label.setText("")

        except Exception as e:
            self.disk_info_label.setText(f"<span style='color:#ef4444'>Error: {e}</span>")

    def clean_apt_cache(self):
        """Clean APT package cache."""
        if not self.confirm_action("Clean APT Cache", "Remove all downloaded .deb files from the package cache?"):
            return

        self.set_status("Cleaning APT cache...", "working")

        def run_clean():
            try:
                self.log("Cleaning APT cache...", "COMMAND")
                result = self.sudo_handler.run_command(['apt-get', 'clean'], timeout=30)
                if result.returncode == 0:
                    self.log("APT cache cleaned", "SUCCESS")
                    self.set_status("APT cache cleaned", "success")
                else:
                    self.log(f"Failed to clean APT cache: {result.stderr}", "ERROR")
                    self.set_status("Clean failed", "error")
            except Exception as e:
                self.log(f"APT clean error: {e}", "ERROR")
                self.set_status("Clean failed", "error")

        self.start_worker(run_clean)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self.refresh_disk_info)

    def remove_old_kernels(self):
        """Remove old kernel packages."""
        if not self.confirm_action(
            "Remove Old Kernels",
            "Remove unused kernel packages?\n\n"
            "This uses 'apt autoremove' which removes old kernels and dependencies."
        ):
            return

        self.set_status("Removing old kernels...", "working")

        def run_remove():
            try:
                self.log("Running apt autoremove...", "COMMAND")
                result = self.sudo_handler.run_command(
                    ['apt-get', 'autoremove', '-y'],
                    timeout=300
                )
                if result.returncode == 0:
                    self.log("Old packages removed", "SUCCESS")
                    self.set_status("Autoremove complete", "success")
                else:
                    self.log(f"Autoremove failed: {result.stderr}", "ERROR")
                    self.set_status("Autoremove failed", "error")
            except Exception as e:
                self.log(f"Autoremove error: {e}", "ERROR")
                self.set_status("Autoremove failed", "error")

        self.start_worker(run_remove)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(5000, self.refresh_disk_info)

    def trim_journal_logs(self):
        """Trim systemd journal logs."""
        if not self.confirm_action(
            "Trim Journal Logs",
            "Remove systemd journal entries older than 7 days?"
        ):
            return

        self.set_status("Trimming logs...", "working")

        def run_trim():
            try:
                self.log("Trimming journal logs (7 day retention)...", "COMMAND")
                result = self.sudo_handler.run_command(
                    ['journalctl', '--vacuum-time=7d'],
                    timeout=30
                )
                if result.returncode == 0:
                    self.log("Journal logs trimmed", "SUCCESS")
                    self.set_status("Logs trimmed", "success")
                else:
                    self.log(f"Journal trim failed: {result.stderr}", "ERROR")
                    self.set_status("Trim failed", "error")
            except Exception as e:
                self.log(f"Journal trim error: {e}", "ERROR")
                self.set_status("Trim failed", "error")

        self.start_worker(run_trim)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self.refresh_disk_info)

    def clean_tmp(self):
        """Clean old temporary files."""
        if not self.confirm_action(
            "Clean Temporary Files",
            "Remove files from /tmp that are older than 7 days?"
        ):
            return

        self.set_status("Cleaning /tmp...", "working")

        def run_clean():
            try:
                self.log("Cleaning old temporary files...", "COMMAND")
                result = self.sudo_handler.run_command(
                    ['find', '/tmp', '-type', 'f', '-mtime', '+7', '-delete'],
                    timeout=30
                )
                if result.returncode == 0:
                    self.log("Temporary files cleaned", "SUCCESS")
                    self.set_status("/tmp cleaned", "success")
                else:
                    self.log(f"Tmp clean failed: {result.stderr}", "ERROR")
                    self.set_status("Clean failed", "error")
            except Exception as e:
                self.log(f"Tmp clean error: {e}", "ERROR")
                self.set_status("Clean failed", "error")

        self.start_worker(run_clean)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self.refresh_disk_info)

    def run_full_cleanup(self):
        """Run all cleanup operations sequentially."""
        if not self.confirm_action(
            "Full Cleanup",
            "This will run all cleanup operations:\n\n"
            "• Clean APT cache\n"
            "• Remove old kernels (autoremove)\n"
            "• Trim journal logs (7 days)\n"
            "• Clean old temp files\n\n"
            "Continue?"
        ):
            return

        self.set_status("Running full cleanup...", "working")

        def run_all():
            try:
                self.log("=== Full Disk Cleanup Started ===", "COMMAND")

                # 1. APT clean
                self.log("Step 1/4: Cleaning APT cache...", "COMMAND")
                self.sudo_handler.run_command(['apt-get', 'clean'], timeout=30)

                # 2. Autoremove
                self.log("Step 2/4: Removing unused packages...", "COMMAND")
                self.sudo_handler.run_command(['apt-get', 'autoremove', '-y'], timeout=300)

                # 3. Journal trim
                self.log("Step 3/4: Trimming journal logs...", "COMMAND")
                self.sudo_handler.run_command(['journalctl', '--vacuum-time=7d'], timeout=30)

                # 4. Tmp cleanup
                self.log("Step 4/4: Cleaning temporary files...", "COMMAND")
                self.sudo_handler.run_command(
                    ['find', '/tmp', '-type', 'f', '-mtime', '+7', '-delete'],
                    timeout=30
                )

                self.log("=== Full Disk Cleanup Complete ===", "SUCCESS")
                self.set_status("Full cleanup complete", "success")
            except Exception as e:
                self.log(f"Full cleanup error: {e}", "ERROR")
                self.set_status("Cleanup failed", "error")

        self.start_worker(run_all)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10000, self.refresh_disk_info)
