"""Custom transition widgets for the Digital Signage Toolkit."""
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget


class FadeStackedWidget(QStackedWidget):
    """QStackedWidget with fade transition effect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fade_duration = 300  # ms
        self.is_animating = False

    def setCurrentIndex(self, index: int):
        """Set current index with fade animation."""
        current_idx = self.currentIndex()
        if current_idx == index:
            return

        if self.is_animating:
            # If already animating, just snap to end (simple conflict resolution)
            self.widget(current_idx).graphicsEffect().setOpacity(1.0)
            super().setCurrentIndex(index)
            return

        current_widget = self.currentWidget()
        next_widget = self.widget(index)

        if not current_widget or not next_widget:
            super().setCurrentIndex(index)
            return

        # Initialize effects
        self.is_animating = True

        # Ensure effects exist
        if not current_widget.graphicsEffect():
            current_widget.setGraphicsEffect(QGraphicsOpacityEffect(current_widget))
        if not next_widget.graphicsEffect():
            next_widget.setGraphicsEffect(QGraphicsOpacityEffect(next_widget))

        # Fade-in only approach: the old page disappears instantly,
        # the new page fades in. True crossfade is not feasible in
        # QStackedWidget layouts without absolute positioning.
        super().setCurrentIndex(index)
        next_widget.hide()

        # Reset opacity and fade in
        next_widget.graphicsEffect().setOpacity(0.0)
        next_widget.show()

        self.anim = QPropertyAnimation(next_widget.graphicsEffect(), b"opacity")
        self.anim.setDuration(self.fade_duration)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self._on_fade_finished)
        self.anim.start()

    def _on_fade_finished(self):
        self.is_animating = False
