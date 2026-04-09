"""Log Viewer tab for Digital Signage Toolkit."""
import subprocess
from datetime import datetime
from pathlib import Path

from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
)


class LogViewerTab(BaseTab):
    """Log Viewer tab for viewing application logs."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.load_log_file()

    def get_log_directory(self) -> Path:
        """Get the log directory from config, with fallback."""
        log_dir = Path(self.config.get('paths.log_dir', '/var/log/dst-toolkit'))
        if not log_dir.exists():
            # Try fallback path from config
            fallback = self.config.expand_path('paths.log_dir_fallback')
            if fallback:
                fallback_path = Path(fallback)
                if fallback_path.exists():
                    return fallback_path
            # Final fallback: check where the logger is actually writing
            try:
                from digital_signage_toolkit.utils.logger import get_logger
                logger = get_logger()
                if logger.log_dir.exists():
                    return logger.log_dir
            except Exception:
                pass
        return log_dir

    def setup_ui(self):
        """Set up the Log Viewer tab UI."""
        # Header
        header_label = QLabel("Application Logs Viewer")
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #e0e0e0; padding: 10px;")
        self.layout.addWidget(header_label)

        # Controls
        controls_layout = QHBoxLayout()

        # Log file selection
        controls_layout.addWidget(QLabel("Log File:"))
        self.log_file_combo = QComboBox()
        self.log_file_combo.addItems([
            "Application Log",
            "Audit Log",
            "Error Log",
            "System Log (journalctl)"
        ])
        self.log_file_combo.currentTextChanged.connect(self.load_log_file)
        controls_layout.addWidget(self.log_file_combo)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_log_file)
        refresh_btn.setProperty("class", "primary")
        controls_layout.addWidget(refresh_btn)

        # Auto-refresh checkbox
        self.auto_refresh_check = QCheckBox("Auto-refresh (10s)")

        self.auto_refresh_check.toggled.connect(self.toggle_auto_refresh)
        controls_layout.addWidget(self.auto_refresh_check)

        # Lines to show
        controls_layout.addWidget(QLabel("Show last:"))
        self.log_lines_spin = QSpinBox()
        self.log_lines_spin.setRange(50, 10000)
        self.log_lines_spin.setValue(500)
        self.log_lines_spin.setSuffix(" lines")
        self.log_lines_spin.valueChanged.connect(self.load_log_file)
        controls_layout.addWidget(self.log_lines_spin)

        controls_layout.addStretch()

        # Open log directory button
        open_dir_btn = QPushButton("📁 Open Log Directory")
        open_dir_btn.clicked.connect(self.open_log_directory)

        controls_layout.addWidget(open_dir_btn)

        self.layout.addLayout(controls_layout)

        # Log display
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-family: 'Courier New', monospace;
                font-size: 12pt;
                border: 1px solid #3c3c3c;
                padding: 5px;
            }
        """)
        self.layout.addWidget(self.log_viewer)

        # Status label
        self.log_status_label = QLabel("Ready")
        self.log_status_label.setStyleSheet("color: #b0b0b0; padding: 5px; font-size: 10pt;")
        self.layout.addWidget(self.log_status_label)

        # Auto-refresh timer
        self.log_refresh_timer = QTimer()
        self.log_refresh_timer.timeout.connect(self.load_log_file)

    def load_log_file(self):
        """Load the selected log file into the viewer."""
        try:
            selected = self.log_file_combo.currentText()

            # Handle System Log (journalctl)
            if selected == "System Log (journalctl)":
                num_lines = self.log_lines_spin.value()
                result = self.main_window.sudo_handler.run_command(
                    ['journalctl', '-n', str(num_lines), '-xe'],
                    timeout=10
                )
                if result.returncode == 0:
                    content = result.stdout
                    if not content.strip():
                        content = "--- No system logs found matching criteria ---"
                    self.log_viewer.setPlainText(content)
                    self.log_status_label.setText(f"✅ Loaded {num_lines} lines from system journal")
                else:
                    self.log_viewer.setPlainText(f"Error fetching system logs:\n{result.stderr}")
                    self.log_status_label.setText("❌ Error fetching journalctl")

                # Scroll to bottom
                cursor = self.log_viewer.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.log_viewer.setTextCursor(cursor)
                return

            # Handle File Logs
            log_file_map = {
                "Application Log": "application.log",
                "Audit Log": "audit.log",
                "Error Log": "error.log"
            }

            log_filename = log_file_map.get(selected, "application.log")

            # Get log directory from config
            log_dir = self.get_log_directory()

            log_file = log_dir / log_filename

            if not log_file.exists():
                self.log_viewer.setPlainText(f"Log file not found: {log_file}\n\nLog directory: {log_dir}")
                self.log_status_label.setText(f"❌ Log file not found: {log_file}")
                return

            # Read last N lines
            num_lines = self.log_lines_spin.value()

            try:
                with open(log_file, encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total_lines = len(lines)

                    if total_lines == 0:
                         self.log_viewer.setPlainText("--- Log file is empty ---")
                         self.log_status_label.setText(f"ℹ️ Log file is empty: {log_filename}")
                         return

                    # Get last N lines
                    if total_lines > num_lines:
                        lines = lines[-num_lines:]
                        truncated = True
                    else:
                        truncated = False

                    content = ''.join(lines)

                    # Add header if truncated
                    if truncated:
                        header = f"--- Showing last {num_lines} lines of {log_filename} ({total_lines} total lines) ---\n\n"
                        content = header + content

                    self.log_viewer.setPlainText(content)

                    # Scroll to bottom
                    cursor = self.log_viewer.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    self.log_viewer.setTextCursor(cursor)

                    # Update status
                    file_size = log_file.stat().st_size / 1024  # KB
                    self.log_status_label.setText(
                        f"✅ Loaded {len(lines)} lines from {log_filename} ({file_size:.1f} KB) | "
                        f"Last updated: {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
                    )
            except PermissionError:
                self.log_viewer.setPlainText(
                    f"Permission denied: Cannot read {log_file}\n\n"
                    f"You may need sudo privileges to view system logs.\n"
                    f"Log directory: {log_dir}"
                )
                self.log_status_label.setText(f"❌ Permission denied: {log_file}")
            except Exception as e:
                self.log_viewer.setPlainText(f"Error reading log file: {e}\n\nFile: {log_file}")
                self.log_status_label.setText(f"❌ Error: {str(e)}")

        except Exception as e:
            self.logger.log_error(e, "LOAD_LOG_FILE")
            self.log_viewer.setPlainText(f"Error: {str(e)}")
            self.log_status_label.setText("❌ Error loading log file")

    def toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh of log viewer."""
        if enabled:
            self.log_refresh_timer.start(10000)  # 10 seconds
        else:
            self.log_refresh_timer.stop()

    def open_log_directory(self):
        """Open the log directory in file manager."""
        try:
            log_dir = self.get_log_directory()

            if log_dir.exists():
                # Try to open with xdg-open (Linux)
                subprocess.Popen(['xdg-open', str(log_dir)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                self.log_status_label.setText(f"📁 Opened log directory: {log_dir}")
            else:
                QMessageBox.warning(
                    self,
                    "Directory Not Found",
                    f"Log directory does not exist:\n{log_dir}"
                )
        except Exception as e:
            self.logger.log_error(e, "OPEN_LOG_DIRECTORY")
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open log directory:\n{str(e)}"
            )
