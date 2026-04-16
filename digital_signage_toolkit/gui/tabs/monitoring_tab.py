"""Monitoring tab for Digital Signage Toolkit."""
import json
from datetime import datetime

from PyQt6.QtWidgets import QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .base_tab import BaseTab


class MonitoringTab(BaseTab):
    """Hardware Monitoring tab for system health and display management."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self._last_thermal_alert_time = 0
        self.setup_ui()
        self.populate_resolutions()
        self.update_monitoring_info()

    def setup_ui(self):
        """Set up the Monitoring tab UI."""
        # System Info
        system_group = QGroupBox("System Information")
        system_layout = QVBoxLayout()

        self.system_info_label = QLabel()
        self.system_info_label.setStyleSheet("font-family: monospace; padding: 10px; color: #e0e0e0; background-color: #27272a; border: 1px solid #3f3f46; border-radius: 4px;")
        system_layout.addWidget(self.system_info_label)

        system_group.setLayout(system_layout)
        self.layout.addWidget(system_group)

        # Hardware Health
        health_group = QGroupBox("Hardware Health")
        health_layout = QVBoxLayout()

        self.health_label = QLabel()
        self.health_label.setStyleSheet("font-family: monospace; padding: 10px; color: #e0e0e0; background-color: #27272a; border: 1px solid #3f3f46; border-radius: 4px;")
        health_layout.addWidget(self.health_label)

        health_group.setLayout(health_layout)
        self.layout.addWidget(health_group)

        # Operations (New Section)
        ops_group = QGroupBox("System Operations")
        ops_layout = QHBoxLayout()

        self.restart_net_btn = QPushButton("Restart Networking")
        self.restart_net_btn.setProperty("class", "warning")
        self.restart_net_btn.clicked.connect(self._on_restart_network)
        ops_layout.addWidget(self.restart_net_btn)

        self.wake_screen_btn = QPushButton("Wake Screen")
        self.wake_screen_btn.clicked.connect(self._on_wake_screen)
        ops_layout.addWidget(self.wake_screen_btn)

        self.stop_player_btn = QPushButton("Stop Player")
        self.stop_player_btn.setProperty("class", "danger")
        self.stop_player_btn.clicked.connect(lambda: self._on_toggle_player("stop"))
        ops_layout.addWidget(self.stop_player_btn)

        self.start_player_btn = QPushButton("Start Player")
        self.start_player_btn.setProperty("class", "success")
        self.start_player_btn.clicked.connect(lambda: self._on_toggle_player("start"))
        ops_layout.addWidget(self.start_player_btn)

        ops_group.setLayout(ops_layout)
        self.layout.addWidget(ops_group)

        # Diagnostics & Reporting
        diag_group = QGroupBox("Diagnostics & Reporting")
        diag_layout = QHBoxLayout()

        self.test_pattern_btn = QPushButton("Display Test Pattern")
        self.test_pattern_btn.clicked.connect(self._on_test_pattern)
        diag_layout.addWidget(self.test_pattern_btn)

        self.export_btn = QPushButton("Export System Report")
        self.export_btn.clicked.connect(self._on_export_info)
        diag_layout.addWidget(self.export_btn)

        diag_group.setLayout(diag_layout)
        self.layout.addWidget(diag_group)

        # Display Resolution
        display_group = QGroupBox("Display Resolution")
        display_layout = QVBoxLayout()

        self.current_resolution_label = QLabel("Checking...")
        self.current_resolution_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        display_layout.addWidget(self.current_resolution_label)

        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Change Resolution:"))

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Auto-detect (recommended)"])
        resolution_layout.addWidget(self.resolution_combo)

        set_resolution_btn = QPushButton("Set Resolution")
        set_resolution_btn.clicked.connect(self.set_display_resolution)
        resolution_layout.addWidget(set_resolution_btn)

        display_layout.addLayout(resolution_layout)
        display_group.setLayout(display_layout)
        self.layout.addWidget(display_group)

        # TeamViewer Status
        tv_group = QGroupBox("Remote Connectivity")
        tv_layout = QVBoxLayout()

        self.tv_status_label = QLabel("Checking...")
        self.tv_status_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        tv_layout.addWidget(self.tv_status_label)

        tv_group.setLayout(tv_layout)
        self.layout.addWidget(tv_group)

        self.layout.addStretch()

    def populate_resolutions(self):
        """Populate the resolution combo box with available resolutions."""
        available_resolutions = self.system_ops.get_available_resolutions()
        if available_resolutions:
            self.resolution_combo.clear()
            self.resolution_combo.addItem("Auto-detect (recommended)")
            for res in available_resolutions:
                self.resolution_combo.addItem(res)

    def update_monitoring_info(self):
        """Update monitoring information."""
        # System info
        sys_info = self.hardware_monitor.get_system_info()
        uptime = self.system_ops.get_uptime()
        network = self.system_ops.get_active_interface()

        sys_text = f"<span style='color:#a1a1aa'>Hostname:</span> <b>{sys_info.get('hostname', 'N/A')}</b><br>"
        sys_text += f"<span style='color:#a1a1aa'>OS:</span> {sys_info.get('os', 'N/A')} {sys_info.get('os_version', 'N/A')}<br>"
        sys_text += f"<span style='color:#a1a1aa'>Architecture:</span> {sys_info.get('architecture', 'N/A')}<br>"
        sys_text += f"<span style='color:#a1a1aa'>Uptime:</span> {uptime}<br>"
        sys_text += f"<span style='color:#a1a1aa'>Interface:</span> {network['interface']} ({network['ip']})"
        self.system_info_label.setText(sys_text)

        # Hardware health
        cpu_temp = self.hardware_monitor.get_cpu_temperature()
        cpu_usage = self.hardware_monitor.get_cpu_usage()
        mem = self.hardware_monitor.get_memory_usage()
        disk = self.hardware_monitor.get_disk_usage()

        # Thermal monitoring
        is_critical, max_temp, zone_name = self.hardware_monitor.check_thermal_critical(threshold=85.0)

        health_text = f"<span style='color:#a1a1aa'>CPU Usage:</span> <b>{cpu_usage:.1f}%</b><br>"

        if max_temp:
            status_color = "#ef4444" if is_critical else "#22c55e"
            status_icon = "⚠️" if is_critical else "✓"
            health_text += f"<span style='color:#a1a1aa'>Temperature:</span> <span style='color:{status_color}'>{status_icon} {max_temp:.1f}°C</span>"
            if zone_name:
                health_text += f" <span style='font-size:10px'>({zone_name})</span>"
            health_text += "<br>"
        elif cpu_temp:
            health_text += f"<span style='color:#a1a1aa'>Temperature:</span> {cpu_temp:.1f}°C<br>"

        health_text += f"<span style='color:#a1a1aa'>Memory:</span> {mem['used_gb']:.1f}GB / {mem['total_gb']:.1f}GB ({mem['percent']:.1f}%)<br>"
        health_text += f"<span style='color:#a1a1aa'>Disk:</span> {disk['used_gb']:.1f}GB / {disk['total_gb']:.1f}GB ({disk['percent']:.1f}%)"
        self.health_label.setText(health_text)

        # Check if critical thermal logic needed (omitted for brevity, assume handled by monitor class or keep existing logic if needed)
        # Existing logic:
        if is_critical and max_temp:
           if (datetime.now().timestamp() - self._last_thermal_alert_time) > 300:
               self.logger.log_security_event("THERMAL_CRITICAL", f"Critical temp: {max_temp:.1f}")
               self.log(f"⚠️ CRITICAL: Temperature {max_temp:.1f}°C!", "ERROR")
               self._last_thermal_alert_time = datetime.now().timestamp()
               # Auto-trigger email alert
               try:
                   from ...core.alert_manager import AlertManager
                   alert_mgr = AlertManager(self.main_window.config)
                   hostname = self.system_ops.get_hostname() or 'unknown'
                   alert_mgr.send_alert(
                       f'[DST Alert] {hostname} — Critical Temperature',
                       f'Kiosk {hostname} has reached critical temperature: {max_temp:.1f}°C ({zone_name or "unknown zone"}).\n'
                       f'Threshold: 85.0°C\n'
                       f'Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                   )
               except Exception:
                   pass  # Alert failure should not crash monitoring

        # Display resolution
        resolution = self.system_ops.get_display_resolution()
        preferred = None
        try:
            preferred = self.system_ops.get_preferred_resolution()
        except Exception:
            preferred = None

        if resolution:
            label_text = f"Current Resolution: {resolution}"
            if preferred and preferred != resolution:
                label_text += f" (Preferred: {preferred})"
            elif preferred and preferred == resolution:
                label_text += " (native/preferred)"
            else:
                label_text += " (auto-detected)"
            self.current_resolution_label.setText(label_text)
        else:
            self.current_resolution_label.setText("Current Resolution: Unable to detect")

        # Update combo logic (same as before)
        available_resolutions = self.system_ops.get_available_resolutions()
        if available_resolutions:
            current_text = self.resolution_combo.currentText()
            self.resolution_combo.clear()
            self.resolution_combo.addItem("Auto-detect (recommended)")
            for res in available_resolutions:
                self.resolution_combo.addItem(res)
                if resolution and res == resolution:
                    self.resolution_combo.setCurrentText(res)
            if current_text == "Auto-detect (recommended)":
                self.resolution_combo.setCurrentIndex(0)

        # Connectivity Status
        tv_status = self.hardware_monitor.check_teamviewer_status()

        tv_color = "#22c55e" if tv_status['online'] else "#ef4444"
        tv_icon = "✓" if tv_status['online'] else "✕"

        tv_text_base = f"<span style='color:#a1a1aa'>TeamViewer:</span> <span style='color:{tv_color}'>{tv_icon} {'Online' if tv_status['online'] else 'Offline'}</span>"
        tv_text_base += f" (Installed: {'Yes' if tv_status['installed'] else 'No'})<br>"

        self.tv_status_label.setText(tv_text_base + "<span style='color:#a1a1aa'>Ping 8.8.8.8:</span> <b style='color:#a1a1aa'>Checking...</b>")

        def on_ping_finished(latency):
            latency_color = "#22c55e" if latency and latency < 100 else "#eab308" if latency and latency < 300 else "#ef4444"
            latency_text = f"{latency:.1f} ms" if latency else "Timeout"
            tv_text = tv_text_base + f"<span style='color:#a1a1aa'>Ping 8.8.8.8:</span> <b style='color:{latency_color}'>{latency_text}</b>"
            self.tv_status_label.setText(tv_text)

        worker = self.start_worker(self.system_ops.get_ping_latency)
        worker.result_signal.connect(on_ping_finished)

    def _on_restart_network(self):
        """Handle network restart."""
        self.log("Restarting networking services...", "INFO")
        self.restart_net_btn.setEnabled(False)
        self.main_window.statusBar().showMessage("Restarting Network...")

        def on_finished(success):
            if success:
                self.log("Networking restarted successfully", "SUCCESS")
                self.set_status("Network Restarted", "success")
            else:
                self.log("Failed to restart networking", "ERROR")
                self.set_status("Restart Failed", "error")
            self.restart_net_btn.setEnabled(True)
            self.update_monitoring_info()

        worker = self.start_worker(self.system_ops.restart_networking)
        worker.finished_signal.connect(on_finished)

    def _on_wake_screen(self):
        self.log("Sending wake signal to screen...", "INFO")
        self.wake_screen_btn.setEnabled(False)
        def on_finished(success):
            if success:
                self.log("Wake signal sent", "SUCCESS")
            else:
                self.log("Failed to wake screen", "ERROR")
            self.wake_screen_btn.setEnabled(True)
        worker = self.start_worker(self.system_ops.wake_screen)
        worker.finished_signal.connect(on_finished)

    def _on_toggle_player(self, action):
        self.log(f"{action.title()}ing Rise Player...", "INFO")
        btn = self.start_player_btn if action == 'start' else self.stop_player_btn
        btn.setEnabled(False)
        def on_finished(success):
            if success:
                self.log(f"Rise Player {action}ed successfully", "SUCCESS")
            else:
                self.log(f"Failed to {action} Rise Player", "ERROR")
            btn.setEnabled(True)
        worker = self.start_worker(self.system_ops.toggle_rise_player, action)
        worker.finished_signal.connect(on_finished)

    def _on_test_pattern(self):
        """Show the test pattern dialog."""
        from ..dialogs import TestPatternDialog
        dialog = TestPatternDialog(self)
        dialog.exec()

    def _on_export_info(self):
        """Export system info to JSON."""
        try:
            sys_info = self.hardware_monitor.get_system_info()
            health = {
                "cpu_temp": self.hardware_monitor.get_cpu_temperature(),
                "cpu_usage": self.hardware_monitor.get_cpu_usage(),
                "memory": self.hardware_monitor.get_memory_usage(),
                "disk": self.hardware_monitor.get_disk_usage()
            }
            network = self.system_ops.get_active_interface()

            report = {
                "timestamp": datetime.now().isoformat(),
                "system": sys_info,
                "health": health,
                "network": network,
                "uptime": self.system_ops.get_uptime(),
                "resolution": self.system_ops.get_display_resolution(),
                "rise_player_status": self.system_ops.get_service_status("rise-vision-player")
            }

            # Generate filename
            hostname = sys_info.get("hostname", "unknown")
            filename = f"report_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save System Report", filename, "JSON Files (*.json)"
            )

            if save_path:
                with open(save_path, 'w') as f:
                    json.dump(report, f, indent=4)
                self.log(f"System report saved to {save_path}", "SUCCESS")
                self.set_status("Report Exported", "success")

        except Exception as e:
            self.log(f"Failed to export report: {e}", "ERROR")
            self.set_status("Export Failed", "error")

    def set_display_resolution(self):
        """Set display resolution."""
        selected = self.resolution_combo.currentText()

        # If "Auto-detect" is selected, use None to let system use native resolution
        if selected == "Auto-detect (recommended)":
            selected_res = None
        else:
            selected_res = selected

        def on_finished(success):
            if success:
                if selected_res is None:
                    self.log("Using auto-detected native resolution", "SUCCESS")
                    self.set_status("Using native resolution", "success")
                else:
                    self.log(f"Display resolution set to {selected_res}", "SUCCESS")
                    self.set_status(f"Resolution set to {selected_res}", "success")
                self.update_monitoring_info()
            else:
                if selected_res is None:
                    self.log("Using current display resolution (no change needed)", "INFO")
                    self.set_status("Resolution unchanged", "info")
                else:
                    self.log("Failed to set display resolution", "ERROR")
                    self.set_status("Resolution Change Failed", "error")

        worker = self.start_worker(self.system_ops.set_display_resolution, selected_res)
        worker.finished_signal.connect(on_finished)
