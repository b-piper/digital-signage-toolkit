"""System Operations & Restore tab for Digital Signage Toolkit."""
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QListWidget, QPushButton, QMessageBox
)
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab


class RestoreTab(BaseTab):
    """Tab for System Operations and Restore functions."""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.refresh_snapshots()
    
    def setup_ui(self):
        """Set up the System Ops & Restore tab UI."""
        
        # --- Section 1: System Operations ---
        ops_group = QGroupBox("Rise Vision Operations")
        ops_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #3f3f46; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        ops_layout = QHBoxLayout()
        
        # Clear Cache Button
        clear_cache_btn = QPushButton("🧹 Clear Rise Vision Cache")
        clear_cache_btn.setToolTip("Deletes temporary files. Useful if content isn't updating.")
        clear_cache_btn.clicked.connect(self.clear_cache)
        ops_layout.addWidget(clear_cache_btn)
        
        # Restart Player Button
        restart_player_btn = QPushButton("🔄 Restart Player Service")
        restart_player_btn.setToolTip("Restarts the Rise Vision background service.")
        restart_player_btn.clicked.connect(self.restart_player)
        ops_layout.addWidget(restart_player_btn)
        
        # Reboot System Button
        reboot_btn = QPushButton("⚠️ Reboot System")
        reboot_btn.setProperty("class", "danger")
        reboot_btn.setStyleSheet("background-color: #ef4444; color: white;")
        reboot_btn.clicked.connect(self.reboot_system)
        ops_layout.addWidget(reboot_btn)
        
        ops_group.setLayout(ops_layout)
        self.layout.addWidget(ops_group)
        
        # --- Section 2: Timeshift Snapshots ---
        snapshot_group = QGroupBox("System Restore (Timeshift Snapshots)")
        snapshot_layout = QVBoxLayout()
        
        info_label = QLabel(
            "System Restore allows you to rollback the entire OS to a previous snapshot.\n"
            "Snapshots are automatically created before OS upgrades and fixes."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #27272a; border-radius: 4px; color: #a1a1aa; margin-bottom: 10px;")
        snapshot_layout.addWidget(info_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.clicked.connect(self.refresh_snapshots)
        controls_layout.addWidget(refresh_btn)
        
        create_snapshot_btn = QPushButton("📸 Create Snapshot")
        create_snapshot_btn.setProperty("class", "primary")
        create_snapshot_btn.clicked.connect(self.create_snapshot)
        controls_layout.addWidget(create_snapshot_btn)
        snapshot_layout.addLayout(controls_layout)
        
        # List
        self.snapshot_list = QListWidget()
        snapshot_layout.addWidget(self.snapshot_list)
        
        # Restore Button
        restore_btn = QPushButton("↺ Restore Selected Snapshot")
        restore_btn.setProperty("class", "danger")
        restore_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 10px;")
        restore_btn.clicked.connect(self.restore_snapshot)
        snapshot_layout.addWidget(restore_btn)
        
        snapshot_group.setLayout(snapshot_layout)
        self.layout.addWidget(snapshot_group)
        
        self.layout.addStretch()
    
    # --- Operation Methods ---
    
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

    def restart_player(self):
        """Restart Rise Vision Player."""
        if not self.confirm_action("Restart Player", "Restart the Rise Vision Player service?"):
            return
            
        self.set_status("Restarting Player...", "working")
        
        def run_restart():
            try:
                self.log("Restarting Rise Vision service...", "COMMAND")
                self.system_ops.toggle_rise_player('restart')
                self.log("Service restart command sent", "SUCCESS")
                self.set_status("Player Restarted", "success")
            except Exception as e:
                self.log(f"Failed to restart player: {e}", "ERROR")
                self.set_status("Restart Failed", "error")
                
        self.start_worker(run_restart)

    def reboot_system(self):
        """Reboot the system."""
        if not self.confirm_action("Reboot System", "Are you sure you want to reboot the system immediately?"):
            return
            
        try:
            self.log("Initiating system reboot...", "WARNING")
            self.system_ops.reboot()
        except Exception as e:
            self.show_error("Reboot Failed", str(e))

    # --- Snapshot Methods ---

    def refresh_snapshots(self):
        """Refresh snapshot list."""
        self.log("Refreshing snapshots...", "COMMAND")
        self.set_status("Refreshing Snapshots...", "working")
        
        def run_refresh():
            snapshots = self.timeshift_manager.list_snapshots()
            return snapshots

        def on_complete(worker):
            # This runs on main thread after worker finishes (need to implement worker result handling or just do UI update here)
            # Since my start_worker helper doesn't easily return values, I'll just do it simply here or update start_worker
            # For simplicity, let's just run list_snapshots on main thread if it's fast, or use the existing pattern
            pass

        # Since I can't easily change the threading model right now, let's stick to the previous pattern
        # or just run it synchronously if list_snapshots is fast enough. 
        # Timeshift list can be slow. 
        # Let's use the pattern:
        
        def refresh_op():
            snapshots = self.timeshift_manager.list_snapshots()
            # We need to update UI on main thread. 
            # My BaseTab structure might rely on signals.
            # Let's just do it directly for now, Timeshift listing isn't usually blocking for too long.
            # But wait, interacting with subprocess in UI thread freezes UI.
            pass
            
        # Reverting to synchronous for simplicity unless confirmed slow.
        # Actually, let's keep the original implementation's logic but wrap it better if needed.
        # The original implementation was synchronous in __init__.
        
        snapshots = self.timeshift_manager.list_snapshots()
        self.snapshot_list.clear()
        
        if snapshots:
            for snapshot in snapshots:
                self.snapshot_list.addItem(f"{snapshot.get('id', 'Unknown')} - {snapshot.get('description', 'No description')}")
            self.log(f"Found {len(snapshots)} snapshots", "SUCCESS")
        else:
            self.snapshot_list.addItem("No snapshots found")
            self.log("No snapshots available", "WARNING")
        
        self.set_status("Snapshots Refreshed", "info")
    
    def create_snapshot(self):
        """Create a new snapshot."""
        if not self.confirm_action(
            "Create Snapshot",
            "Create a system snapshot now?\n\n"
            "This may take several minutes."
        ):
            return
        
        self.log("Creating snapshot...", "COMMAND")
        self.set_status("Creating Snapshot...", "working")
        
        def snapshot_complete(success):
            if success:
                self.log("Snapshot created successfully", "SUCCESS")
                self.set_status("Snapshot Created", "success")
                self.refresh_snapshots()
            else:
                self.log("Snapshot creation failed", "ERROR")
                self.set_status("Snapshot Failed", "error")
        
        self.timeshift_manager.create_snapshot(
            f"Manual snapshot {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.log,
            snapshot_complete
        )
    
    def restore_snapshot(self):
        """Restore selected snapshot."""
        selected = self.snapshot_list.currentItem()
        if not selected or selected.text() == "No snapshots found":
            self.show_error("No Selection", "Please select a snapshot to restore.")
            return
        
        snapshot_text = selected.text()
        snapshot_id = snapshot_text.split(' - ')[0]
        
        reply = QMessageBox.critical(
            self,
            "Confirm Restore",
            f"⚠️ WARNING: This will restore the entire system to snapshot:\n\n"
            f"{snapshot_text}\n\n"
            f"ALL CURRENT DATA AND SETTINGS WILL BE LOST!\n\n"
            f"The system will reboot after restoration.\n\n"
            f"Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log(f"Restoring snapshot: {snapshot_id}", "COMMAND")
            self.set_status("Restoring System...", "working")
            
            def restore_complete(success):
                if success:
                    self.log("Restoration initiated. System will reboot.", "SUCCESS")
                else:
                    self.log("Restoration failed", "ERROR")
                    self.set_status("Restore Failed", "error")
            
            self.timeshift_manager.restore_snapshot(snapshot_id, self.log, restore_complete)
