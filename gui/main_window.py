"""Main GUI window."""
import qtawesome as qta
from digital_signage_toolkit.core.hardware_monitor import HardwareMonitor
from digital_signage_toolkit.core.software_installer import SoftwareInstaller
from digital_signage_toolkit.core.system_ops import SystemOperations
from digital_signage_toolkit.core.timeshift_manager import TimeshiftManager
from digital_signage_toolkit.core.watchdog import WatchdogManager
from digital_signage_toolkit.gui.tabs import AlertsTab
from digital_signage_toolkit.gui.transitions import FadeStackedWidget
from digital_signage_toolkit.gui.widgets import LogConsole, StatusWidget
from digital_signage_toolkit.utils.config import Config
from digital_signage_toolkit.utils.logger import get_logger
from digital_signage_toolkit.utils.preflight_checks import PreflightChecker
from digital_signage_toolkit.utils.sudo_handler import SudoHandler
from PyQt6.QtCore import QSettings, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class WorkerThread(QThread):
    """Background worker thread for long-running operations."""
    log_signal = pyqtSignal(str, str)  # message, level
    status_signal = pyqtSignal(str, str)  # message, status_type
    progress_signal = pyqtSignal(int)  # percentage
    finished_signal = pyqtSignal(bool)  # success
    result_signal = pyqtSignal(object)  # For returning arbitrary objects

    def __init__(self, operation_func, *args, **kwargs):
        super().__init__()
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Run the operation function."""
        try:
            result = self.operation_func(*self.args, **self.kwargs)
            self.result_signal.emit(result)
            self.finished_signal.emit(result if isinstance(result, bool) else True)
        except Exception as e:
            self.log_signal.emit(f"Error: {e}", "ERROR")
            self.finished_signal.emit(False)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.logger = get_logger()
        self.sudo_handler = SudoHandler()
        self.system_ops = SystemOperations(self.sudo_handler)
        self.software_installer = SoftwareInstaller(self.sudo_handler, self.config)
        self.watchdog_manager = WatchdogManager(self.sudo_handler, self.config)
        self.timeshift_manager = TimeshiftManager(self.sudo_handler, self.config)
        self.hardware_monitor = HardwareMonitor()

        self.current_worker = None
        self.settings = QSettings('SouthwesternCC', 'DigitalSignageToolkit')
        self.init_ui()
        self._setup_keyboard_shortcuts()
        self._restore_window_state()
        self.start_hardware_monitoring()

        self.log("Application started as root", "SUCCESS")
        self.status_widget.set_status("Ready", "success")

        # Run preflight checks in background
        self.run_preflight_checks()

    def closeEvent(self, event):
        """Handle application close - cleanup resources."""
        # Save window state
        self._save_window_state()
        # Stop hardware monitoring
        if hasattr(self, 'monitor_timer'):
            self.monitor_timer.stop()

        # Stop any running worker threads
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait(3000)  # Wait up to 3 seconds

        event.accept()

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for tab navigation."""
        for i in range(9):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i+1}"), self)
            shortcut.activated.connect(lambda idx=i: self._switch_to_tab(idx))

    def _switch_to_tab(self, index: int):
        """Switch to tab at given index (if valid)."""
        if 0 <= index < self.nav_list.count():
            self.nav_list.setCurrentRow(index)

    def _save_window_state(self):
        """Save window geometry and state to settings."""
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())

    def _restore_window_state(self):
        """Restore window geometry and state from settings."""
        geometry = self.settings.value('geometry')
        state = self.settings.value('windowState')
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Southwestern CC - Digital Signage Toolkit")
        self.setGeometry(100, 100, 1280, 850)

        # Central widget
        central_widget = QWidget()
        central_widget.setProperty("class", "background")
        self.setCentralWidget(central_widget)

        # Host Layout (Sidebar + content)
        host_layout = QHBoxLayout(central_widget)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(240)
        sidebar_widget.setStyleSheet("background-color: #18181b; border-right: 1px solid #27272a;")
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        # App Title / Logo Area
        title_frame = QFrame()
        title_frame.setFixedHeight(80)
        title_frame.setStyleSheet("background-color: #18181b; border-bottom: 1px solid #27272a;")
        title_layout = QVBoxLayout(title_frame)
        title_label = QLabel("Digital Signage\nToolkit")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f4f4f5; border: none;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label)
        sidebar_layout.addWidget(title_frame)

        # Navigation List
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("sidebar")
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav_list.currentRowChanged.connect(self.switch_tab)

        # Add Navigation Items
        self.add_nav_item("Master Setup", "fa5s.rocket")
        self.add_nav_item("OS Upgrade", "fa5s.arrow-circle-up")
        self.add_nav_item("Watchdog", "fa5s.shield-alt")
        self.add_nav_item("System Restore", "fa5s.history")
        self.add_nav_item("Scheduler", "fa5s.clock")
        self.add_nav_item("Alerts", "fa5s.bell")
        self.add_nav_item("Monitoring", "fa5s.chart-line")
        self.add_nav_item("Logs", "fa5s.file-alt")

        sidebar_layout.addWidget(self.nav_list)

        # Status Widget at bottom of sidebar
        self.status_widget = StatusWidget()
        self.status_widget.setStyleSheet("background-color: #27272a; border-top: 1px solid #3f3f46; padding: 10px;")
        sidebar_layout.addWidget(self.status_widget)

        # Sidebar Footer (About & Exit)
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(0)

        about_btn = QPushButton(" About")
        about_btn.setIcon(qta.icon('fa5s.info-circle', color='#a1a1aa'))
        about_btn.setStyleSheet("""
            QPushButton {
                background-color: #18181b; 
                text-align: left; 
                padding: 10px 20px; 
                border: none;
                color: #a1a1aa;
            }
            QPushButton:hover { background-color: #27272a; color: #f4f4f5; }
        """)
        about_btn.clicked.connect(self.show_about_dialog)
        footer_layout.addWidget(about_btn)

        exit_btn = QPushButton(" Exit Application")
        exit_btn.setIcon(qta.icon('fa5s.sign-out-alt', color='#ef4444'))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a; 
                text-align: left; 
                padding: 15px 20px; 
                border: none;
                border-top: 1px solid #3f3f46;
                color: #ef4444;
            }
            QPushButton:hover { background-color: #3f3f46; }
        """)
        exit_btn.clicked.connect(self.close)
        footer_layout.addWidget(exit_btn)
        sidebar_layout.addLayout(footer_layout)

        host_layout.addWidget(sidebar_widget)

        # --- Content Area ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Header for Content
        header_layout = QHBoxLayout()
        self.page_title = QLabel("Dashboard")
        self.page_title.setProperty("class", "header")
        header_layout.addWidget(self.page_title)
        header_layout.addStretch()

        reboot_btn = QPushButton(" Reboot System")
        reboot_btn.setIcon(qta.icon('fa5s.power-off', color='#ffffff'))
        reboot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reboot_btn.setStyleSheet("background-color: #ef4444; color: white;")
        reboot_btn.setToolTip("Clear cache and reboot the kiosk system")
        reboot_btn.clicked.connect(self.reboot_system)
        header_layout.addWidget(reboot_btn)

        content_layout.addLayout(header_layout)

        # Stacked Widget for Pages
        self.page_stack = FadeStackedWidget()

        # Create tabs using separate tab modules
        self._create_tabs()

        content_layout.addWidget(self.page_stack)

        # Log Console (Collapsible-ish)
        log_group = QWidget()
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_label = QLabel("Activity Log")
        log_label.setProperty("class", "subheader")
        log_layout.addWidget(log_label)

        self.log_console = LogConsole()
        self.log_console.setMaximumHeight(150)
        log_layout.addWidget(self.log_console)

        content_layout.addWidget(log_group)

        host_layout.addWidget(content_widget)

        # Select first item
        self.nav_list.setCurrentRow(0)

    def add_nav_item(self, text, icon_name):
        """Add item to navigation list."""
        item = QListWidgetItem(text)
        item.setIcon(qta.icon(icon_name, color="#a1a1aa"))
        item.setData(Qt.ItemDataRole.UserRole, icon_name) # Store icon name
        self.nav_list.addItem(item)

    def switch_tab(self, index):
        """Switch stacked widget page based on list selection."""
        self.page_stack.setCurrentIndex(index)

        # Update page title
        item = self.nav_list.item(index)
        if item:
            self.page_title.setText(item.text())

            # Update icon selection state
            for i in range(self.nav_list.count()):
                it = self.nav_list.item(i)
                icon_name = it.data(Qt.ItemDataRole.UserRole)
                if i == index:
                    # Active color
                    it.setIcon(qta.icon(icon_name, color="#6366f1"))
                else:
                    # Inactive color
                    it.setIcon(qta.icon(icon_name, color="#a1a1aa"))

            # Special logic for hardware monitoring updates
            # Tab 6 is Monitoring (0=Master,1=OS,2=Watchdog,3=Restore,4=Sched,5=Alerts,6=Monitor,7=Logs)
            if index == 6:
                self.monitoring_tab.update_monitoring_info()

    def _create_tabs(self):
        """Create all tabs and add to stack."""
        from digital_signage_toolkit.gui.tabs import (
            LogViewerTab,
            MasterSetupTab,
            MonitoringTab,
            OSUpgradeTab,
            RestoreTab,
            SchedulerTab,
            WatchdogTab,
        )

        # Create tab instances
        self.master_setup_tab = MasterSetupTab(self)
        self.os_upgrade_tab = OSUpgradeTab(self)
        self.watchdog_tab = WatchdogTab(self)
        self.restore_tab = RestoreTab(self)
        self.scheduler_tab = SchedulerTab(self)
        self.monitoring_tab = MonitoringTab(self)
        self.log_viewer_tab = LogViewerTab(self)
        self.alerts_tab = AlertsTab(self)

        # Add tabs to stacked widget
        self.page_stack.addWidget(self.master_setup_tab)
        self.page_stack.addWidget(self.os_upgrade_tab)
        self.page_stack.addWidget(self.watchdog_tab)
        self.page_stack.addWidget(self.restore_tab)
        self.page_stack.addWidget(self.scheduler_tab)
        self.page_stack.addWidget(self.alerts_tab)
        self.page_stack.addWidget(self.monitoring_tab)
        self.page_stack.addWidget(self.log_viewer_tab)
        # Add tabs to stacked widget

    def log(self, message: str, level: str = "INFO"):
        """Log a message to the console."""
        if hasattr(self, 'log_console') and self.log_console is not None:
            self.log_console.append_log(message, level)

    def start_hardware_monitoring(self):
        """Start periodic hardware monitoring updates."""
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_monitoring)
        self.monitor_timer.start(5000)  # Update every 5 seconds

    def _update_monitoring(self):
        """Update monitoring information in the Monitoring tab."""
        # Only update if monitoring tab is visible (tab index 6)
        if self.page_stack.currentIndex() == 6 and hasattr(self, 'monitoring_tab'):
            self.monitoring_tab.update_monitoring_info()

    def reboot_system(self):
        """Reboot the system."""
        reply = QMessageBox.warning(
            self,
            "Confirm Reboot",
            "Reboot the system now?\n\nCache will be cleared before reboot.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log("Clearing cache before reboot...", "COMMAND")
            self.log("Rebooting system...", "COMMAND")
            self.system_ops.reboot(clear_cache=True)

    def run_preflight_checks(self):
        """Run preflight checks in background."""
        def check_operation():
            try:
                checker = PreflightChecker(self.sudo_handler)
                results = checker.run_all_checks()

                # Log any warnings or errors
                for check_name, result in results.items():
                    if not result['passed']:
                        self.log(f"Preflight check warning: {check_name} - {result.get('message', 'Failed')}", "WARNING")
            except Exception as e:
                self.logger.log_error(e, "PREFLIGHT_CHECKS")

        self.preflight_worker = WorkerThread(check_operation)
        self.preflight_worker.start()

    def show_about_dialog(self):
        """Show about dialog with version information."""
        from digital_signage_toolkit.gui.dialogs import ModernAboutDialog
        version = self.config.get('version', '2.0.0')
        dialog = ModernAboutDialog(self, version)
        dialog.exec()
