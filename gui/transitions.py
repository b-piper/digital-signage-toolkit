"""Custom transition widgets for the Digital Signage Toolkit."""
from PyQt6.QtWidgets import QStackedWidget, QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QAbstractAnimation

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
            
        # Opacity Animations
        fade_out = QPropertyAnimation(current_widget.graphicsEffect(), b"opacity")
        fade_out.setDuration(self.fade_duration)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        fade_in = QPropertyAnimation(next_widget.graphicsEffect(), b"opacity")
        fade_in.setDuration(self.fade_duration)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # Show next widget immediately but transparent
        next_widget.graphicsEffect().setOpacity(0.0)
        next_widget.show()
        next_widget.raise_()
        
        # Calculate geometry (Next widget should cover current)
        # Note: In a layout, this is tricky. QStackedWidget usually handles geometry.
        # We'll use a simplified approach: Fade Out THEN Fade In (Cross-fade is hard in Layouts without absolute positioning)
        # Actually, standard crossfade in StackedLayout is hard because usually only one is visible.
        # Strategy: Use QStackedWidget's layout behavior. 
        # We will run them sequentially for simplicity in layout management: Out -> Switch -> In.
        # It's less "Apple-like" crossfade but safe for layouts.
        
        # To make it feel faster, we can overlap slightly or just be fast.
        
        self.anim_group = QParallelAnimationGroup()
        # For true crossfade, we'd need them both visible and overlapping.
        # Given the constraints, let's do a fast sequence.
        
        # Actually, let's try a simpler Fade In Only for the new page.
        # The old page disappears instantly, new page fades in.
        
        super().setCurrentIndex(index)
        next_widget.hide() # hide effectively to reset for fade in
        
        # Reset Opacity
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
