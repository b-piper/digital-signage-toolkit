"""OS Upgrade tab for Digital Signage Toolkit."""
import os
import subprocess
import time

from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from digital_signage_toolkit.gui.widgets import SmoothProgressBar
from PyQt6.QtWidgets import QLabel, QPushButton


class OSUpgradeTab(BaseTab):
    """OS Upgrade tab for system upgrades."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()

    def setup_ui(self):
        """Set up the OS Upgrade tab UI."""
        warning_label = QLabel(
            "⚠️ WARNING: OS upgrades take 30-60 minutes and require stable internet connection.\n"
            "Do not unplug power during upgrade. A system snapshot will be created automatically."
        )
        warning_label.setStyleSheet("color: #eab308; padding: 10px; background-color: #27272a; border-radius: 4px; border: 1px solid #3f3f46;")
        warning_label.setWordWrap(True)
        self.layout.addWidget(warning_label)

        self.layout.addWidget(warning_label)

        self.progress = SmoothProgressBar()
        self.layout.addWidget(self.progress)

        start_btn = QPushButton("⬆️ Start OS Upgrade")
        start_btn.setProperty("class", "danger")
        start_btn.setStyleSheet("background-color: #ef4444; color: white;") # Explicit red for danger
        start_btn.clicked.connect(self.run_os_upgrade)
        self.layout.addWidget(start_btn)

        self.layout.addStretch()

    def run_os_upgrade(self):
        """Run OS upgrade operation."""
        # Check disk space (Requirement: 5GB)
        if not self.main_window.system_ops.check_disk_space(min_gb=5.0):
            self.show_error(
                "Insufficient Disk Space",
                "OS Upgrade requires at least 5GB of free disk space.\n\n"
                "Please free up space and try again."
            )
            return

        if not self.show_warning(
            "Confirm OS Upgrade",
            "⚠️ WARNING: This operation takes 30-60 minutes and requires:\n\n"
            "- Stable internet connection (Ethernet recommended)\n"
            "- Uninterrupted power supply\n"
            "- A system snapshot will be created automatically\n\n"
            "Do not close this application or unplug power during upgrade.\n\n"
            "Continue?"
        ):
            return

        self.set_status("Running OS Upgrade...", "working")
        self.progress.setValue(0)

        def os_upgrade_operation():
            try:
                self.log("Starting OS Upgrade...", "INFO")

                # Create snapshot first
                if self.config.get('timeshift.auto_snapshot_before_upgrade', True):
                    self.log("Creating system snapshot before upgrade...", "COMMAND")
                    snapshot_created = False

                    def snapshot_complete(success):
                        nonlocal snapshot_created
                        snapshot_created = success
                        if success:
                            self.log("Snapshot created successfully", "SUCCESS")
                        else:
                            self.log("Snapshot creation failed, continuing anyway", "WARNING")

                    self.timeshift_manager.create_snapshot("Pre-upgrade snapshot", self.log, snapshot_complete)
                    time.sleep(5)

                self.set_progress(10)

                # Fix apt locks
                self.log("Fixing apt locks...", "COMMAND")
                self.system_ops.fix_apt_locks()
                self.log("Apt locks cleared", "SUCCESS")

                # Backup sources.list
                self.log("Backing up sources.list...", "COMMAND")
                backup_path = self.system_ops.backup_sources_list()
                if backup_path:
                    self.log(f"Backup created: {backup_path}", "SUCCESS")

                # Force main mirror
                self.log("Configuring apt sources...", "COMMAND")
                self.system_ops.force_main_mirror()
                self.set_progress(20)

                # Update and dist-upgrade
                self.log("Updating package lists...", "COMMAND")
                success, output = self.system_ops.apt_update()
                if not success:
                    self.log("Update failed", "ERROR")
                    return False

                self.log("Running dist-upgrade...", "COMMAND")
                success, output = self.system_ops.apt_dist_upgrade()
                if not success:
                    self.log("Dist-upgrade failed", "ERROR")
                    return False

                self.set_progress(50)

                # Autoremove
                self.log("Cleaning up packages...", "COMMAND")
                self.system_ops.apt_autoremove()

                # Install update-manager-core if needed
                self.log("Installing update-manager-core...", "COMMAND")
                self.system_ops.install_packages(['update-manager-core'])
                self.set_progress(60)

                # Run do-release-upgrade
                self.log("Starting release upgrade (non-interactive)...", "COMMAND")
                self.log("This may take 30-60 minutes. Please wait...", "WARNING")

                # Set environment and run upgrade
                env = os.environ.copy()
                env['DEBIAN_FRONTEND'] = 'noninteractive'

                result = self.sudo_handler.run_command(
                    ['do-release-upgrade', '-f', 'DistUpgradeViewNonInteractive'],
                    timeout=3600,  # 1 hour
                    env=env
                )

                if result.returncode == 0:
                    self.log("OS Upgrade Complete! Rebooting...", "SUCCESS")
                    self.set_progress(100)
                    self.set_status("Upgrade Complete - Rebooting", "success")

                    self.show_info(
                        "Upgrade Complete",
                        "OS upgrade completed successfully!\n\n"
                        "The system will reboot now."
                    )

                    self.system_ops.reboot()
                    return True
                else:
                    self.log(f"Upgrade failed: {result.stderr}", "ERROR")
                    self.set_status("Upgrade Failed", "error")
                    return False

            except subprocess.TimeoutExpired:
                self.log("Upgrade timed out", "ERROR")
                self.set_status("Upgrade Timed Out", "error")
                return False
            except Exception as e:
                self.log(f"OS Upgrade error: {e}", "ERROR")
                self.set_status("Upgrade Failed", "error")
                return False

        self.start_worker(os_upgrade_operation)
