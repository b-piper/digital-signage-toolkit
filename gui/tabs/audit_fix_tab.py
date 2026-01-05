"""Audit & Fix tab for Digital Signage Toolkit."""
from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QCheckBox, QProgressBar, QPushButton
)
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from digital_signage_toolkit.gui.widgets import SmoothProgressBar


class AuditFixTab(BaseTab):
    """Audit & Fix tab for system maintenance and troubleshooting."""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the Audit & Fix tab UI."""
        options_group = QGroupBox("Fix Options")
        options_layout = QVBoxLayout()
        
        self.fix_updates_check = QCheckBox("Check and install system updates")
        self.fix_updates_check.setChecked(True)
        options_layout.addWidget(self.fix_updates_check)
        
        self.fix_cache_check = QCheckBox("Clear Rise Vision cache")
        self.fix_cache_check.setChecked(True)
        options_layout.addWidget(self.fix_cache_check)
        
        self.fix_permissions_check = QCheckBox("Fix Rise Vision permissions")
        self.fix_permissions_check.setChecked(True)
        options_layout.addWidget(self.fix_permissions_check)
        
        self.fix_reinstall_check = QCheckBox("Reinstall Rise Vision if corrupted")
        self.fix_reinstall_check.setChecked(True)
        options_layout.addWidget(self.fix_reinstall_check)
        
        options_group.setLayout(options_layout)
        self.layout.addWidget(options_group)
        
        options_group.setLayout(options_layout)
        self.layout.addWidget(options_group)
        
        # Emergency Heal Button
        heal_btn = QPushButton("🚑 Emergency Heal (One-Click Fix)")
        heal_btn.setProperty("class", "danger")
        heal_btn.clicked.connect(self.run_emergency_heal)
        self.layout.addWidget(heal_btn)
        
        self.progress = SmoothProgressBar()
        self.layout.addWidget(self.progress)
        
        start_btn = QPushButton("🛠️ Start Audit & Fix")
        start_btn.setProperty("class", "primary")
        start_btn.clicked.connect(self.run_audit_fix)
        self.layout.addWidget(start_btn)
        
        self.layout.addStretch()

    def run_emergency_heal(self):
        """Run quick emergency fix operation."""
        self.set_status("Running Emergency Heal...", "working")
        self.progress.setValue(0)
        
        def heal_operation():
            try:
                self.log("Starting Emergency Heal...", "INFO")
                self.set_progress(10)
                
                # 1. Clear Cache
                self.log("Clearing Rise Vision cache...", "COMMAND")
                self.software_installer.clear_rise_cache(self.log)
                self.set_progress(40)
                
                # 2. Fix Permissions
                self.log("Fixing permissions...", "COMMAND")
                self.software_installer.fix_rise_permissions(
                     self.config.expand_path('paths.player_dir'), self.log
                )
                self.set_progress(70)
                
                # 3. Restart Player
                self.log("Restarting Rise Vision Player...", "COMMAND")
                self.system_ops.toggle_rise_player('restart')
                self.set_progress(100)
                
                self.log("Emergency Heal Complete!", "SUCCESS")
                self.set_status("Heal Complete - Player Restarted", "success")
                
            except Exception as e:
                self.log(f"Emergency Heal Failed: {e}", "ERROR")
                self.set_status("Heal Failed", "error")
        
        self.start_worker(heal_operation)
    
    def run_audit_fix(self):
        """Run audit and fix operation."""
        self.set_status("Running Audit & Fix...", "working")
        self.progress.setValue(0)
        
        def audit_fix_operation():
            try:
                self.log("Starting Audit & Fix...", "INFO")
                
                # Create snapshot if configured
                if self.config.get('timeshift.auto_snapshot_before_fix', True):
                    self.log("Creating system snapshot before fix...", "COMMAND")
                    self.timeshift_manager.create_snapshot("Pre-fix snapshot", self.log, None)
                
                # Updates (mirror Master Setup behaviour)
                if self.fix_updates_check.isChecked() and self.system_ops.check_internet():
                    self.log("Checking for updates...", "COMMAND")
                    success, output = self.system_ops.apt_update()
                    if success:
                        success, output = self.system_ops.apt_upgrade()
                        if success:
                            self.log("System updated", "SUCCESS")
                        else:
                            self.log("Update completed with warnings", "WARNING")
                self.set_progress(20)
                
                # Ensure core kiosk configuration from Master Setup is still applied.
                self.log("Ensuring unattended upgrades are configured...", "COMMAND")
                self.system_ops.configure_apt_auto_upgrades()
                self.log("Removing GUI update notifiers if present...", "COMMAND")
                self.system_ops.remove_packages(['update-notifier', 'update-manager-core', 'update-manager'])
                
                # Required command-line tools
                self.log("Ensuring required tools are installed (curl, wget, unzip, unclutter)...", "COMMAND")
                deps_success, deps_output = self.system_ops.install_packages(
                    ['curl', 'wget', 'unzip', 'unclutter']
                )
                if deps_success:
                    self.log("Required tools are installed", "SUCCESS")
                else:
                    self.log("Some required tools failed to install (see logs for details)", "WARNING")
                
                # TeamViewer installation
                tv_url = self.config.get('urls.teamviewer')
                if tv_url:
                    self.log("Ensuring TeamViewer is installed...", "COMMAND")
                    if self.software_installer.install_teamviewer(tv_url, None, self.log):
                        self.log("TeamViewer is installed or already present", "SUCCESS")
                    else:
                        self.log("TeamViewer installation check failed (see logs for details)", "WARNING")
                
                # Kiosk environment settings
                self.log("Reapplying kiosk display and time settings (Wayland, NTP, display power, native resolution)...", "COMMAND")
                self.system_ops.disable_wayland()
                self.system_ops.configure_timedatectl()
                self.system_ops.configure_display_power()
                if self.system_ops.ensure_native_resolution():
                    self.log("Display set to preferred/native resolution where possible", "SUCCESS")
                else:
                    self.log("Unable to adjust display to native resolution (see logs for details)", "WARNING")
                
                self.set_progress(40)
                
                # Cache
                if self.fix_cache_check.isChecked():
                    self.log("Clearing cache...", "COMMAND")
                    self.software_installer.clear_rise_cache(self.log)
                    self.log("Cache cleared", "SUCCESS")
                self.set_progress(60)
                
                # Permissions
                if self.fix_permissions_check.isChecked():
                    self.log("Fixing permissions...", "COMMAND")
                    self.software_installer.fix_rise_permissions(
                        self.config.expand_path('paths.player_dir'), self.log
                    )
                self.set_progress(80)
                
                # Reinstall if needed
                player_startup_path = Path(self.config.expand_path('paths.player_startup'))
                if self.fix_reinstall_check.isChecked() and (
                    not player_startup_path.exists() or player_startup_path.stat().st_size == 0
                ):
                    self.log("Rise Vision corrupted, reinstalling...", "WARNING")
                    rise_url = self.config.get('urls.rise_vision')
                    
                    def rise_complete(success):
                        if success:
                            self.log("Rise Vision reinstalled", "SUCCESS")
                        self.finish_audit_fix()
                    
                    self.software_installer.install_rise_vision(
                        rise_url, None,
                        self.config.expand_path('paths.player_startup'),
                        self.log, rise_complete
                    )
                    return
                
                self.finish_audit_fix()
                
            except Exception as e:
                self.log(f"Audit & Fix error: {e}", "ERROR")
                self.set_status("Audit & Fix Failed", "error")
        
        self.start_worker(audit_fix_operation)
    
    def finish_audit_fix(self):
        """Complete audit and fix."""
        self.log("Updating watchdog configuration...", "COMMAND")
        self.watchdog_manager.enable()
        self.watchdog_manager.configure_reboot_schedule()
        self.watchdog_manager.configure_autostart()
        
        self.set_progress(100)
        self.log("Audit & Fix Complete!", "SUCCESS")
        self.set_status("Audit & Fix Complete", "success")
