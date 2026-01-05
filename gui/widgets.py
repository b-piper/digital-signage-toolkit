"""Custom GUI widgets."""
from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QTextCursor


class LogConsole(QTextEdit):
    """Real-time log console widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier", 10))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #27272a;
                color: #f4f4f5;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.max_lines = 10000
        self._buffer = []
    
    def append_log(self, message: str, level: str = "INFO"):
        """Append a log message with color coding."""
        colors = {
            "INFO": "#f4f4f5",
            "SUCCESS": "#22c55e",
            "WARNING": "#eab308",
            "ERROR": "#ef4444",
            "COMMAND": "#3b82f6"
        }
        
        color = colors.get(level, colors["INFO"])
        timestamp = QTimer().remainingTime()  # Simple timestamp
        formatted = f'<span style="color: {color};">[{level}] {message}</span><br>'
        
        self._buffer.append(formatted)
        
        # Limit buffer size
        if len(self._buffer) > self.max_lines:
            self._buffer = self._buffer[-self.max_lines:]
        
        # Update display
        self.setHtml(''.join(self._buffer))
        
        # Auto-scroll to bottom
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
    
    def clear_log(self):
        """Clear the log console."""
        self._buffer = []
        self.clear()


class StatusWidget(QWidget):
    """Status display widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #27272a;
                color: #f4f4f5;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #3f3f46;
            }
        """)
        self.layout.addWidget(self.status_label)
    
    def set_status(self, message: str, status_type: str = "info"):
        """Set status message with color coding."""
        colors = {
            "info": "#f4f4f5",
            "success": "#22c55e",
            "warning": "#eab308",
            "error": "#ef4444",
            "working": "#3b82f6"
        }
        
        color = colors.get(status_type, colors["info"])
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: #27272a;
                color: {color};
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #3f3f46;
            }}
        """)



class SmoothProgressBar(QProgressBar):
    """ProgressBar with smooth transition animation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(400) # ms
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def setValue(self, value):
        """Set value with animation."""
        if value == self.value():
            return
            
        # Stop previous animation
        self.animation.stop()
        
        # Animate to new value
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()
        
        # Standard update text logic is handled by base class, 
        # but animation changes the 'value' property over time.
