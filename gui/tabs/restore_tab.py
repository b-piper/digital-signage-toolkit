"""System Restore tab for Digital Signage Toolkit."""
from datetime import datetime

from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QVBoxLayout


class RestoreTab(BaseTab):
    """Tab for Timeshift system snapshot management."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.refresh_snapshots()

    def setup_ui(self):
        """Set up the System Restore tab UI."""

        # --- Timeshift Snapshots ---
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

        # Action buttons
        action_layout = QHBoxLayout()

        restore_btn = QPushButton("↺ Restore Selected Snapshot")
        restore_btn.setProperty("class", "danger")
        restore_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 10px;")
        restore_btn.clicked.connect(self.restore_snapshot)
        action_layout.addWidget(restore_btn)

        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.setStyleSheet("background-color: #71717a; color: white; padding: 10px;")
        delete_btn.clicked.connect(self.delete_snapshot)
        action_layout.addWidget(delete_btn)

        snapshot_layout.addLayout(action_layout)

        snapshot_group.setLayout(snapshot_layout)
        self.layout.addWidget(snapshot_group)

        self.layout.addStretch()

    # --- Snapshot Methods ---

    def refresh_snapshots(self):
        """Refresh snapshot list."""
        self.log("Refreshing snapshots...", "COMMAND")
        self.set_status("Refreshing Snapshots...", "working")

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

    def delete_snapshot(self):
        """Delete the selected snapshot."""
        selected = self.snapshot_list.currentItem()
        if not selected or selected.text() == "No snapshots found":
            self.show_error("No Selection", "Please select a snapshot to delete.")
            return

        snapshot_text = selected.text()
        snapshot_id = snapshot_text.split(' - ')[0]

        if not self.confirm_action(
            "Delete Snapshot",
            f"Delete snapshot:\n\n{snapshot_text}\n\nThis cannot be undone."
        ):
            return

        self.log(f"Deleting snapshot: {snapshot_id}", "COMMAND")
        self.set_status("Deleting Snapshot...", "working")

        try:
            success = self.timeshift_manager.delete_snapshot(snapshot_id)
            if success:
                self.log("Snapshot deleted", "SUCCESS")
                self.set_status("Snapshot Deleted", "success")
                self.refresh_snapshots()
            else:
                self.log("Failed to delete snapshot", "ERROR")
                self.set_status("Delete Failed", "error")
        except Exception as e:
            self.log(f"Delete error: {e}", "ERROR")
            self.set_status("Delete Failed", "error")

