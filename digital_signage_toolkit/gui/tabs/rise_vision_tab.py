"""Rise Vision management tab for Digital Signage Toolkit."""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .base_tab import BaseTab

class RiseVisionTab(BaseTab):
    """Tab for Rise Vision Player operations and Live Previews."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        """Set up the Rise Vision tab UI."""

        # --- Player Status ---
        status_group = QGroupBox("Rise Vision Player Status")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Checking...")
        self.status_label.setStyleSheet(
            "font-family: monospace; padding: 12px; color: #e0e0e0; "
            "background-color: #27272a; border: 1px solid #3f3f46; border-radius: 6px;"
        )
        status_layout.addWidget(self.status_label)

        refresh_btn = QPushButton("🔄 Refresh Status")
        refresh_btn.clicked.connect(self.refresh_status)
        status_layout.addWidget(refresh_btn)

        status_group.setLayout(status_layout)
        self.layout.addWidget(status_group)

        # --- Player Operations ---
        ops_group = QGroupBox("Player Operations")
        ops_layout = QVBoxLayout()

        # Row 1: Start / Stop / Restart
        svc_row = QHBoxLayout()

        start_btn = QPushButton("▶️ Start Player")
        start_btn.setStyleSheet("background-color: #22c55e; color: white;")
        start_btn.setToolTip("Start the Rise Vision Player service")
        start_btn.clicked.connect(lambda: self._toggle_player('start'))
        svc_row.addWidget(start_btn)

        stop_btn = QPushButton("⏹️ Stop Player")
        stop_btn.setStyleSheet("background-color: #eab308; color: white;")
        stop_btn.setToolTip("Stop the Rise Vision Player service")
        stop_btn.clicked.connect(lambda: self._toggle_player('stop'))
        svc_row.addWidget(stop_btn)

        restart_btn = QPushButton("🔄 Restart Player")
        restart_btn.setToolTip("Restart the Rise Vision Player service")
        restart_btn.clicked.connect(lambda: self._toggle_player('restart'))
        svc_row.addWidget(restart_btn)

        ops_layout.addLayout(svc_row)

        # Row 2: Cache & Reboot
        maint_row = QHBoxLayout()

        clear_cache_btn = QPushButton("🧹 Clear Rise Vision Cache")
        clear_cache_btn.setToolTip("Deletes temporary files. Useful if content isn't updating.")
        clear_cache_btn.clicked.connect(self.clear_cache)
        maint_row.addWidget(clear_cache_btn)

        reboot_btn = QPushButton("⚠️ Reboot System")
        reboot_btn.setProperty("class", "danger")
        reboot_btn.setStyleSheet("background-color: #ef4444; color: white;")
        reboot_btn.setToolTip("Reboot the system (clears cache first)")
        reboot_btn.clicked.connect(self.reboot_system)
        maint_row.addWidget(reboot_btn)

        ops_layout.addLayout(maint_row)

        ops_group.setLayout(ops_layout)
        self.layout.addWidget(ops_group)

        # --- Live Preview & TV Control ---
        tv_group = QGroupBox("Live Screen & TV Control")
        tv_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Click Snapshot Screen to view live display output")
        self.preview_label.setStyleSheet("background-color: #000000; color: #a1a1aa; font-weight: bold;")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        tv_layout.addWidget(self.preview_label)
        
        tv_btns = QHBoxLayout()
        refresh_preview = QPushButton("📸 Snapshot Screen")
        refresh_preview.clicked.connect(self.take_snapshot)
        tv_btns.addWidget(refresh_preview)
        
        tv_on = QPushButton("📺 Turn TV ON (CEC)")
        tv_on.clicked.connect(lambda: self.toggle_tv(True))
        tv_btns.addWidget(tv_on)
        
        tv_off = QPushButton("🔌 Turn TV OFF (CEC)")
        tv_off.clicked.connect(lambda: self.toggle_tv(False))
        tv_btns.addWidget(tv_off)
        
        tv_layout.addLayout(tv_btns)
        tv_group.setLayout(tv_layout)
        self.layout.addWidget(tv_group)

        self.layout.addStretch()

    def refresh_status(self):
        """Refresh Rise Vision player status display."""
        try:
            rise_status = self.system_ops.get_rise_player_status()
            svc_active = rise_status.get('service_active', False)
            renderer_running = rise_status.get('renderer_running', False)
            renderer_count = rise_status.get('renderer_count', 0)
            memory_mb = rise_status.get('memory_usage_mb', 0)

            if svc_active and renderer_running:
                icon = "✅"
                color = "#22c55e"
            elif svc_active:
                icon = "⚠️"
                color = "#eab308"
            else:
                icon = "❌"
                color = "#ef4444"

            text = f"<span style='color:{color}; font-size:16px; font-weight:bold'>{icon} "
            text += f"{'Running' if svc_active else 'Stopped'}</span><br><br>"
            text += f"<span style='color:#a1a1aa'>Service:</span> {'Active' if svc_active else 'Inactive'}<br>"
            text += f"<span style='color:#a1a1aa'>Renderer Processes:</span> {renderer_count}<br>"
            if memory_mb > 0:
                text += f"<span style='color:#a1a1aa'>Renderer Memory:</span> {memory_mb:.0f} MB<br>"

            self.status_label.setText(text)
        except Exception as e:
            self.status_label.setText(f"<span style='color:#ef4444'>Error checking status: {e}</span>")

    def _toggle_player(self, action):
        """Start, stop, or restart the Rise Vision Player."""
        action_labels = {'start': 'Start', 'stop': 'Stop', 'restart': 'Restart'}
        label = action_labels.get(action, action)

        if action in ('stop', 'restart'):
            if not self.confirm_action(
                f"{label} Player",
                f"{label} the Rise Vision Player service?"
            ):
                return

        self.set_status(f"{label}ing Player...", "working")

        def run_toggle():
            try:
                self.log(f"{label}ing Rise Vision service...", "COMMAND")
                self.system_ops.toggle_rise_player(action)
                self.log(f"Service {action} command sent", "SUCCESS")
                self.set_status(f"Player {label}ed", "success")
            except Exception as e:
                self.log(f"Failed to {action} player: {e}", "ERROR")
                self.set_status(f"{label} Failed", "error")

        self.start_worker(run_toggle)
        # Refresh status after a short delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self.refresh_status)

    def clear_cache(self):
        """Clear Rise Vision cache."""
        if not self.confirm_action("Clear Cache", "Are you sure you want to clear the Rise Vision Player cache?"):
            return

        self.set_status("Clearing Cache...", "working")

        def run_clear():
            try:
                self.log("Clearing Rise Vision cache...", "COMMAND")
                self.software_installer.clear_rise_cache(self.log)
                self.log("Cache cleared successfully", "SUCCESS")
                self.set_status("Cache Cleared", "success")
            except Exception as e:
                self.log(f"Failed to clear cache: {e}", "ERROR")
                self.set_status("Clear Cache Failed", "error")

        self.start_worker(run_clear)

    def reboot_system(self):
        """Reboot the system."""
        if not self.confirm_action(
            "Reboot System",
            "Are you sure you want to reboot the system immediately?\n\n"
            "The cache will be cleared before rebooting."
        ):
            return

        try:
            self.log("Clearing cache and initiating system reboot...", "WARNING")
            self.system_ops.reboot(clear_cache=True)
        except Exception as e:
            self.show_error("Reboot Failed", str(e))

    def take_snapshot(self):
        """Take a snapshot and display it."""
        path = "/tmp/dst_preview.png"
        self.preview_label.setText("Taking screenshot...")
        
        def run_snap():
            return self.system_ops.take_screenshot(path)
            
        def on_snap_done(success):
            if success and os.path.exists(path):
                pixmap = QPixmap(path)
                scaled = pixmap.scaledToHeight(200, Qt.TransformationMode.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.setText("Screenshot failed or display unavailable.")
                
        from ..main_window import WorkerThread
        self.snap_worker = WorkerThread(run_snap)
        self.snap_worker.finished_signal.connect(on_snap_done)
        self.snap_worker.start()

    def toggle_tv(self, power_on):
        """Toggle TV power using CEC."""
        action = "ON" if power_on else "OFF"
        if not self.confirm_action(f"Turn TV {action}", f"Turn physical TV {action} via HDMI-CEC?"):
            return
            
        def run_toggle():
            self.log(f"Sending TV {action} command...", "COMMAND")
            success = self.system_ops.toggle_tv_power(power_on)
            if success:
                self.log(f"TV turned {action}", "SUCCESS")
                self.set_status(f"TV turned {action}", "success")
            else:
                self.log("Failed to toggle TV power via CEC", "ERROR")
                
        self.start_worker(run_toggle)
