"""Custom GUI widgets."""
from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QTextCursor
from PyQt6.QtWidgets import QCheckBox, QLabel, QProgressBar, QTextEdit, QVBoxLayout, QWidget


class StyledCheckBox(QCheckBox):
    """Custom checkbox with a visible checkmark indicator.

    Replaces the default Qt checkbox which only fills with a solid color,
    making it difficult to distinguish checked vs unchecked states.
    This draws a clear white ✓ checkmark inside the indicator box.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QCheckBox {
                spacing: 10px;
                color: #e4e4e7;
                padding: 4px 0px;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #52525b;
                border-radius: 5px;
                background: #18181b;
            }
            QCheckBox::indicator:hover {
                border-color: #6366f1;
                background: #27272a;
            }
            QCheckBox::indicator:checked {
                background: #6366f1;
                border-color: #6366f1;
            }
            QCheckBox::indicator:checked:hover {
                background: #4f46e5;
                border-color: #4f46e5;
            }
        """)

    def paintEvent(self, event):
        """Override paint to draw a checkmark when checked."""
        super().paintEvent(event)

        if self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Calculate the indicator rect position
            # The indicator is drawn at the left side of the checkbox
            indicator_size = 20
            spacing = 2  # border width
            y_offset = (self.height() - indicator_size) / 2

            # Draw the checkmark inside the indicator area
            pen = QPen(QColor("#ffffff"), 2.5, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            # Checkmark path - scaled to fit inside the 20x20 indicator
            x_start = spacing + 1
            check_x = x_start + 5
            check_y = y_offset + 11
            mid_x = x_start + 9
            mid_y = y_offset + 15
            end_x = x_start + 16
            end_y = y_offset + 6

            painter.drawLine(QPointF(check_x, check_y), QPointF(mid_x, mid_y))
            painter.drawLine(QPointF(mid_x, mid_y), QPointF(end_x, end_y))

            painter.end()


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
