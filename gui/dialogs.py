"""Custom dialogs for the Digital Signage Toolkit."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import QDialog, QFrame, QLabel, QPushButton, QVBoxLayout
import qtawesome as qta


class ModernAboutDialog(QDialog):
    """Modern styled About dialog."""

    def __init__(self, parent=None, version="2.0.0"):
        super().__init__(parent)
        self.version = version
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("About")
        self.setFixedSize(400, 350)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Container frame
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #18181b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)
        container_layout.setContentsMargins(30, 40, 30, 30)

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.rocket', color='#6366f1').pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("border: none;")
        container_layout.addWidget(icon_label)

        # Title
        title_label = QLabel("Digital Signage Toolkit")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f4f4f5; border: none;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title_label)

        # Version
        version_label = QLabel(f"Version {self.version}")
        version_label.setStyleSheet("color: #a1a1aa; font-size: 13px; border: none;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(version_label)

        # Description
        desc_label = QLabel(
            "Management utility for Rise Vision kiosks running Ubuntu Linux.\n\n"
            "Developed for Southwestern Community College."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #d4d4d4; font-size: 13px; margin-top: 10px; border: none;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(desc_label)

        container_layout.addStretch()

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e0e0e0;
                border: 1px solid #3f3f46;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.accept)
        container_layout.addWidget(close_btn)

        layout.addWidget(container)


class TestPatternDialog(QDialog):
    """Fullscreen test pattern dialog for pixel checking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.BlankCursor)

        self.colors = [
            Qt.GlobalColor.red,
            Qt.GlobalColor.green,
            Qt.GlobalColor.blue,
            Qt.GlobalColor.white,
            Qt.GlobalColor.black,
            "gradient"
        ]
        self.current_index = 0

        # Info label (fades out)
        self.info_label = QLabel("Click to cycle colors. Press ESC to exit.", self)
        self.info_label.setStyleSheet("color: white; font-size: 24px; background-color: rgba(0,0,0,100); padding: 20px; border-radius: 10px;")
        self.info_label.adjustSize()

        # Center label
        self.info_label.rect()
        # We'll center in resizeEvent or just roughly center
        self.info_label.move(100, 100) # Temporary

        # Timer to hide label
        QTimer.singleShot(3000, self.info_label.hide)

    def paintEvent(self, event):
        """Paint the solid color or gradient."""
        painter = QPainter(self)
        current = self.colors[self.current_index]

        if current == "gradient":
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0.0, Qt.GlobalColor.red)
            gradient.setColorAt(0.2, Qt.GlobalColor.yellow)
            gradient.setColorAt(0.4, Qt.GlobalColor.green)
            gradient.setColorAt(0.6, Qt.GlobalColor.cyan)
            gradient.setColorAt(0.8, Qt.GlobalColor.blue)
            gradient.setColorAt(1.0, Qt.GlobalColor.magenta)
            painter.fillRect(self.rect(), QBrush(gradient))
        else:
            painter.fillRect(self.rect(), QColor(current))

    def mousePressEvent(self, event):
        """Cycle color on click."""
        self.current_index = (self.current_index + 1) % len(self.colors)
        self.update()

    def keyPressEvent(self, event):
        """Exit on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.accept()

    def resizeEvent(self, event):
        """Center info label."""
        if hasattr(self, 'info_label'):
            self.info_label.move(
                (self.width() - self.info_label.width()) // 2,
                (self.height() - self.info_label.height()) // 2
            )
        super().resizeEvent(event)
