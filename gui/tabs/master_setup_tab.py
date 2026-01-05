"""Master Setup tab for Digital Signage Toolkit."""
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QLabel, QLineEdit, QCheckBox, 
    QProgressBar, QPushButton
)
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from digital_signage_toolkit.utils.validators import validate_hostname, sanitize_hostname


class MasterSetupTab(BaseTab):
    """Master Setup tab for initial system configuration."""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the Master Setup tab UI."""
        # Hostname section
        hostname_group = QGroupBox("Device Configuration")
        hostname_layout = QVBoxLayout()
        
        current_hostname_label = QLabel("Current Hostname:")
        current_hostname_label.setToolTip("The current system hostname. This identifies the device on the network.")
        hostname_layout.addWidget(current_hostname_label)
        
        self.current_hostname_label = QLabel(self.system_ops.get_hostname())
        self.current_hostname_label.setProperty("class", "success")
        self.current_hostname_label.setStyleSheet("font-weight: bold;")
        self.current_hostname_label.setToolTip("Current system hostname")
        hostname_layout.addWidget(self.current_hostname_label)
        
        new_hostname_label = QLabel("New Hostname (leave empty to keep current):")
        new_hostname_label.setToolTip("Enter a new hostname to change the device name. Leave empty to keep current hostname.")
        hostname_layout.addWidget(new_hostname_label)
        
        self.new_hostname_input = QLineEdit()
        self.new_hostname_input.setToolTip("New hostname (alphanumeric, hyphens, dots allowed)")
        hostname_layout.addWidget(self.new_hostname_input)
        
        hostname_group.setLayout(hostname_layout)
        self.layout.addWidget(hostname_group)
        
        # Software installation section
        software_group = QGroupBox("Software Installation")
        software_layout = QVBoxLayout()
        
        self.install_teamviewer_check = QCheckBox("Install TeamViewer")
        self.install_teamviewer_check.setChecked(True)
        self.install_teamviewer_check.setToolTip("Install TeamViewer for remote access and support")
        software_layout.addWidget(self.install_teamviewer_check)
        
        self.install_rise_check = QCheckBox("Install Rise Vision Player")
        self.install_rise_check.setChecked(True)
        self.install_rise_check.setToolTip("Install Rise Vision Player for digital signage display")
        software_layout.addWidget(self.install_rise_check)
        
        software_group.setLayout(software_layout)
        self.layout.addWidget(software_group)
        
        # Progress bar
        self.progress = QProgressBar()
        self.layout.addWidget(self.progress)
        
        # Start button
        start_btn = QPushButton("🚀 Start Master Setup")
        start_btn.setProperty("class", "primary")
        start_btn.setToolTip("Begin the master setup process. This will configure the system, install software, and set up the digital signage environment.")
        start_btn.clicked.connect(self.run_master_setup)
        self.layout.addWidget(start_btn)
        
        self.layout.addStretch()
    
    def run_master_setup(self):
        """Run master setup operation."""
        if not self.confirm_action(
            "Confirm Master Setup",
            "This will configure a new PC with hostname, software, and system settings.\n\n"
            "Continue?"
        ):
            return
        
        self.set_status("Running Master Setup...", "working")
        self.progress.setValue(0)
        
        def master_setup_operation():
            try:
                self.log("Starting Master Setup...", "INFO")
                
                # Hostname
                new_hostname = self.new_hostname_input.text().strip()
                if new_hostname:
                    # Validate hostname before setting
                    if not validate_hostname(new_hostname):
                        self.log(f"Invalid hostname format: {new_hostname}", "ERROR")
                        self.log("Hostname must be alphanumeric with hyphens, max 253 chars", "WARNING")
                    else:
                        sanitized = sanitize_hostname(new_hostname)
                        self.log(f"Setting hostname to {sanitized}...", "COMMAND")
                        if self.system_ops.set_hostname(sanitized):
                            self.log(f"Hostname set to {sanitized}", "SUCCESS")
                            self.update_label_text(self.current_hostname_label, sanitized)
                        else:
                            self.log("Failed to set hostname", "ERROR")
                self.set_progress(10)
                
                # Updates
                self.log("Configuring automatic updates...", "COMMAND")
                self.system_ops.configure_apt_auto_upgrades()
                self.log("Removing update notifiers...", "COMMAND")
                self.system_ops.remove_packages(['update-notifier', 'update-manager-core', 'update-manager'])
                self.set_progress(20)
                
                # Install dependencies
                self.log("Installing dependencies...", "COMMAND")
                success, output = self.system_ops.install_packages(['curl', 'wget', 'unzip', 'unclutter'])
                if success:
                    self.log("Dependencies installed", "SUCCESS")
                else:
                    self.log(f"Dependency installation issues: {output}", "WARNING")
                self.set_progress(30)
                
                # System updates
                if self.system_ops.check_internet():
                    self.log("Updating system packages...", "COMMAND")
                    success, output = self.system_ops.apt_update()
                    if success:
                        self.log("Package list updated", "SUCCESS")
                        success, output = self.system_ops.apt_upgrade()
                        if success:
                            self.log("System upgraded", "SUCCESS")
                        else:
                            self.log("Upgrade completed with warnings", "WARNING")
                    else:
                        self.log("Update failed (may be offline)", "WARNING")
                self.set_progress(50)
                
                # TeamViewer
                if self.install_teamviewer_check.isChecked():
                    self.log("Installing TeamViewer...", "COMMAND")
                    tv_url = self.config.get('urls.teamviewer')
                    if self.software_installer.install_teamviewer(tv_url, None, self.log):
                        self.log("TeamViewer installed", "SUCCESS")
                    else:
                        self.log("TeamViewer installation failed", "ERROR")
                self.set_progress(60)
                
                # Disable Wayland
                self.log("Disabling Wayland...", "COMMAND")
                self.system_ops.disable_wayland()
                self.set_progress(70)
                
                # Rise Vision
                if self.install_rise_check.isChecked():
                    self.log("Installing Rise Vision Player...", "COMMAND")
                    rise_url = self.config.get('urls.rise_vision')
                    
                    def rise_complete(success):
                        if success:
                            self.log("Rise Vision installed", "SUCCESS")
                        else:
                            self.log("Rise Vision installation failed", "ERROR")
                        self.set_progress(90)
                        self.finish_master_setup()
                    
                    self.software_installer.install_rise_vision(
                        rise_url, None, 
                        self.config.expand_path('paths.player_startup'),
                        self.log, rise_complete
                    )
                    return  # Will continue in callback
                
                self.set_progress(90)
                self.finish_master_setup()
                
            except Exception as e:
                self.log(f"Master setup error: {e}", "ERROR")
                self.set_status("Master Setup Failed", "error")
        
        self.start_worker(master_setup_operation)
    
    def finish_master_setup(self):
        """Complete master setup configuration."""
        self.log("Configuring watchdog...", "COMMAND")
        self.watchdog_manager.enable()
        self.log("Configuring reboot schedule...", "COMMAND")
        self.watchdog_manager.configure_reboot_schedule()
        self.log("Configuring autostart...", "COMMAND")
        self.watchdog_manager.configure_autostart()
        self.log("Optimizing settings...", "COMMAND")
        self.system_ops.configure_timedatectl()
        self.system_ops.configure_display_power()
        self.log("Ensuring display is using native resolution (if available)...", "COMMAND")
        if self.system_ops.ensure_native_resolution():
            self.log("Display set to preferred/native resolution where possible", "SUCCESS")
        else:
            self.log("Unable to adjust display to native resolution (see logs for details)", "WARNING")
        
        self.set_progress(100)
        self.log("Master Setup Complete! Reboot recommended.", "SUCCESS")
        self.set_status("Master Setup Complete", "success")
        
        self.show_info(
            "Setup Complete",
            "Master Setup completed successfully!\n\n"
            "Please reboot the system to apply all changes."
        )
