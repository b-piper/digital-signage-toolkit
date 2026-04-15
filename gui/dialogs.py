"""Custom dialogs for the Digital Signage Toolkit."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter
from PyQt6.QtWidgets import QDialog, QFrame, QLabel, QPushButton, QVBoxLayout
import qtawesome as qta


class ModernAboutDialog(QDialog):
    """Modern styled About dialog."""

    def __init__(self, parent=None, version="2.4.5"):
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
    """Fullscreen test pattern dialog for display diagnostics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Use showFullScreen() approach which works on both X11 and Wayland
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.setStyleSheet("background-color: black;")

        self.patterns = [
            "smpte_bars",
            "grid",
            "red", "green", "blue",
            "white", "black",
            "gradient"
        ]
        self.current_index = 0

        # Info label (fades out)
        self.info_label = QLabel(
            "Click or press → to cycle patterns.  Press ESC to exit.\n\n"
            "Patterns: SMPTE Bars → Grid → Red → Green → Blue → White → Black → Gradient",
            self
        )
        self.info_label.setStyleSheet(
            "color: white; font-size: 20px; background-color: rgba(0,0,0,180);"
            "padding: 20px; border-radius: 10px;"
        )
        self.info_label.adjustSize()

        # Timer to hide label
        QTimer.singleShot(4000, self.info_label.hide)

    def showEvent(self, event):
        """Go fullscreen after the window is shown."""
        super().showEvent(event)
        self.showFullScreen()

    def paintEvent(self, event):
        """Paint the current test pattern."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pattern = self.patterns[self.current_index]

        if pattern == "smpte_bars":
            self._draw_smpte_bars(painter, w, h)
        elif pattern == "grid":
            self._draw_grid(painter, w, h)
        elif pattern == "gradient":
            gradient = QLinearGradient(0, 0, w, 0)
            gradient.setColorAt(0.0, QColor(255, 0, 0))
            gradient.setColorAt(0.17, QColor(255, 255, 0))
            gradient.setColorAt(0.33, QColor(0, 255, 0))
            gradient.setColorAt(0.5, QColor(0, 255, 255))
            gradient.setColorAt(0.67, QColor(0, 0, 255))
            gradient.setColorAt(0.83, QColor(255, 0, 255))
            gradient.setColorAt(1.0, QColor(255, 0, 0))
            painter.fillRect(0, 0, w, h, QBrush(gradient))
        else:
            color_map = {
                "red": QColor(255, 0, 0),
                "green": QColor(0, 255, 0),
                "blue": QColor(0, 0, 255),
                "white": QColor(255, 255, 255),
                "black": QColor(0, 0, 0),
            }
            painter.fillRect(0, 0, w, h, color_map.get(pattern, QColor(0, 0, 0)))

    def _draw_smpte_bars(self, painter: QPainter, w: int, h: int):
        """Draw SMPTE-style color bars."""
        # Top 2/3: main color bars
        bar_height = int(h * 0.67)
        colors_top = [
            QColor(192, 192, 192),  # Gray
            QColor(192, 192, 0),    # Yellow
            QColor(0, 192, 192),    # Cyan
            QColor(0, 192, 0),      # Green
            QColor(192, 0, 192),    # Magenta
            QColor(192, 0, 0),      # Red
            QColor(0, 0, 192),      # Blue
        ]
        bar_w = w / len(colors_top)
        for i, color in enumerate(colors_top):
            painter.fillRect(int(i * bar_w), 0, int(bar_w) + 1, bar_height, color)

        # Middle strip: complementary colors
        strip_height = int(h * 0.08)
        strip_y = bar_height
        colors_mid = [
            QColor(0, 0, 192),      # Blue
            QColor(19, 19, 19),     # Black
            QColor(192, 0, 192),    # Magenta
            QColor(19, 19, 19),     # Black
            QColor(0, 192, 192),    # Cyan
            QColor(19, 19, 19),     # Black
            QColor(192, 192, 192),  # Gray
        ]
        for i, color in enumerate(colors_mid):
            painter.fillRect(int(i * bar_w), strip_y, int(bar_w) + 1, strip_height, color)

        # Bottom strip: grayscale ramp
        bottom_y = strip_y + strip_height
        bottom_h = h - bottom_y
        num_steps = 16
        step_w = w / num_steps
        for i in range(num_steps):
            gray = int(255 * i / (num_steps - 1))
            painter.fillRect(int(i * step_w), bottom_y, int(step_w) + 1, bottom_h, QColor(gray, gray, gray))

    def _draw_grid(self, painter: QPainter, w: int, h: int):
        """Draw alignment grid with resolution info."""
        # Black background
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0))

        # Grid lines
        grid_color = QColor(40, 40, 40)
        fine_spacing = 50
        coarse_spacing = 200

        pen = painter.pen()

        # Fine grid
        pen.setColor(grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(0, w, fine_spacing):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, fine_spacing):
            painter.drawLine(0, y, w, y)

        # Coarse grid
        pen.setColor(QColor(80, 80, 80))
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(0, w, coarse_spacing):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, coarse_spacing):
            painter.drawLine(0, y, w, y)

        # Border rectangle (1px inside edges)
        pen.setColor(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(1, 1, w - 3, h - 3)

        # Crosshair at center
        cx, cy = w // 2, h // 2
        pen.setColor(QColor(255, 0, 0))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(cx - 40, cy, cx + 40, cy)
        painter.drawLine(cx, cy - 40, cx, cy + 40)
        painter.drawEllipse(cx - 20, cy - 20, 40, 40)

        # Corner markers
        marker_len = 30
        pen.setColor(QColor(0, 255, 0))
        painter.setPen(pen)
        for corner_x, corner_y, dx, dy in [
            (5, 5, 1, 1), (w - 5, 5, -1, 1),
            (5, h - 5, 1, -1), (w - 5, h - 5, -1, -1)
        ]:
            painter.drawLine(corner_x, corner_y, corner_x + dx * marker_len, corner_y)
            painter.drawLine(corner_x, corner_y, corner_x, corner_y + dy * marker_len)

        # Resolution text at center
        font = QFont("monospace", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        text = f"{w} × {h}"
        text_rect = painter.fontMetrics().boundingRect(text)
        painter.drawText(
            cx - text_rect.width() // 2,
            cy + 60,
            text
        )

        # Label font
        font_small = QFont("monospace", 12)
        painter.setFont(font_small)
        painter.setPen(QColor(160, 160, 160))
        painter.drawText(cx - 60, cy + 85, "Display Resolution")

    def mousePressEvent(self, event):
        """Cycle pattern on click."""
        self.current_index = (self.current_index + 1) % len(self.patterns)
        self.update()

    def keyPressEvent(self, event):
        """Handle key presses."""
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Space):
            self.current_index = (self.current_index + 1) % len(self.patterns)
            self.update()
        elif event.key() == Qt.Key.Key_Left:
            self.current_index = (self.current_index - 1) % len(self.patterns)
            self.update()

    def resizeEvent(self, event):
        """Center info label."""
        if hasattr(self, 'info_label'):
            self.info_label.move(
                (self.width() - self.info_label.width()) // 2,
                (self.height() - self.info_label.height()) // 2
            )
        super().resizeEvent(event)
