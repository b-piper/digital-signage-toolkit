"""Base tab class for Digital Signage Toolkit GUI tabs."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QProgressBar, QLabel
from PyQt6.QtCore import pyqtSignal, QMetaObject, Qt, Q_ARG


class BaseTab(QWidget):
    """Base class for all tab widgets with shared functionality."""
    
    # Signals for thread-safe communication
    log_signal = pyqtSignal(str, str)  # message, level
    status_signal = pyqtSignal(str, str)  # message, status_type
    progress_signal = pyqtSignal(int)  # percentage
    
    def __init__(self, main_window):
        """Initialize base tab.
        
        Args:
            main_window: Reference to the MainWindow instance for accessing
                         shared resources (config, sudo_handler, etc.)
        """
        super().__init__()
        self.main_window = main_window
        # Create main layout
        self.layout = QVBoxLayout(self)
        
        # Connect signals for thread-safe updates
        self.log_signal.connect(self._on_log)
        self.status_signal.connect(self._on_status)
        self.progress_signal.connect(self._on_progress)
    
    def _on_log(self, message: str, level: str):
        """Handle log signal on main thread."""
        self.main_window.log(message, level)
    
    def _on_status(self, message: str, status_type: str):
        """Handle status signal on main thread."""
        self.main_window.status_widget.set_status(message, status_type)
    
    def _on_progress(self, value: int):
        """Handle progress signal on main thread."""
        if hasattr(self, 'progress') and isinstance(self.progress, QProgressBar):
            self.progress.setValue(value)
    
    @property
    def config(self):
        """Access the configuration object."""
        return self.main_window.config
    
    @property
    def sudo_handler(self):
        """Access the sudo handler."""
        return self.main_window.sudo_handler
    
    @property
    def system_ops(self):
        """Access system operations."""
        return self.main_window.system_ops
    
    @property
    def software_installer(self):
        """Access software installer."""
        return self.main_window.software_installer
    
    @property
    def watchdog_manager(self):
        """Access watchdog manager."""
        return self.main_window.watchdog_manager
    
    @property
    def timeshift_manager(self):
        """Access timeshift manager."""
        return self.main_window.timeshift_manager
    
    @property
    def hardware_monitor(self):
        """Access hardware monitor."""
        return self.main_window.hardware_monitor
    
    @property
    def logger(self):
        """Access the logger."""
        return self.main_window.logger
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message (thread-safe via signal)."""
        self.log_signal.emit(message, level)
    
    def set_status(self, message: str, status_type: str = "info"):
        """Set status (thread-safe via signal)."""
        self.status_signal.emit(message, status_type)
    
    def set_progress(self, value: int):
        """Set progress bar value (thread-safe via signal)."""
        self.progress_signal.emit(value)
    
    def update_label_text(self, label: QLabel, text: str):
        """Thread-safe label text update."""
        QMetaObject.invokeMethod(
            label, "setText", 
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text)
        )
    
    def confirm_action(self, title: str, message: str) -> bool:
        """Show a confirmation dialog.
        
        Returns:
            True if user clicked Yes, False otherwise.
        """
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def show_warning(self, title: str, message: str) -> bool:
        """Show a warning dialog with Yes/No buttons.
        
        Returns:
            True if user clicked Yes, False otherwise.
        """
        reply = QMessageBox.warning(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def show_info(self, title: str, message: str):
        """Show an information dialog."""
        QMessageBox.information(self, title, message)
    
    def show_error(self, title: str, message: str):
        """Show an error dialog."""
        QMessageBox.critical(self, title, message)
    
    def start_worker(self, operation_func, *args, **kwargs):
        """Start a worker thread for a long-running operation."""
        from digital_signage_toolkit.gui.main_window import WorkerThread
        worker = WorkerThread(operation_func, *args, **kwargs)
        worker.log_signal.connect(self._on_log)
        self.main_window.current_worker = worker
        worker.start()
        return worker

