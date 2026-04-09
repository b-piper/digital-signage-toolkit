"""Theme definitions for Digital Signage Toolkit."""

class ModernTheme:
    """Modern dark theme based on Zinc palette."""

    # Color Palette (Zinc & Indigo)
    COLORS = {
        "bg_primary": "#18181b",      # Zinc 950
        "bg_secondary": "#27272a",    # Zinc 800
        "bg_tertiary": "#3f3f46",     # Zinc 700
        "text_primary": "#f4f4f5",    # Zinc 100
        "text_secondary": "#a1a1aa",  # Zinc 400
        "accent": "#6366f1",          # Indigo 500
        "accent_hover": "#4f46e5",    # Indigo 600
        "accent_pressed": "#4338ca",  # Indigo 700
        "border": "#3f3f46",          # Zinc 700
        "success": "#22c55e",         # Green 500
        "warning": "#eab308",         # Yellow 500
        "error": "#ef4444",           # Red 500
    }

    # Main Stylesheet
    STYLESHEET = """
        QMainWindow, QDialog {
            background-color: #18181b;
            color: #f4f4f5;
        }
        
        QWidget {
            background-color: #18181b;
            color: #f4f4f5;
            font-family: 'Segoe UI', 'Roboto', sans-serif;
            font-size: 14px;
        }
        
        /* Side Navigation */
        QListWidget#sidebar {
            background-color: #18181b;
            border: none;
            outline: none;
            min-width: 220px;
            max-width: 220px;
            padding-top: 20px;
        }
        
        QListWidget#sidebar::item {
            color: #a1a1aa;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 4px 12px;
            font-weight: 500;
        }
        
        QListWidget#sidebar::item:hover {
            background-color: #27272a;
            color: #f4f4f5;
        }
        
        QListWidget#sidebar::item:selected {
            background-color: #27272a;
            color: #6366f1; /* Indigo Accent */
            border-left: 3px solid #6366f1;
        }
        
        /* Content Area */
        QStackedWidget {
            background-color: #18181b;
            padding: 20px;
        }
        
        /* Cards / Group Boxes */
        QGroupBox {
            background-color: #27272a;
            border: 1px solid #3f3f46;
            border-radius: 8px;
            margin-top: 1.5em; /* Leave space for title */
            padding-top: 15px;
            font-weight: 600;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 15px;
            padding: 0 5px;
            color: #f4f4f5;
            background-color: transparent;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #3f3f46;
            color: #f4f4f5;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 600;
        }
        
        QPushButton:hover {
            background-color: #52525b;
        }
        
        QPushButton:pressed {
            background-color: #27272a;
        }
        
        /* Primary Action Buttons */
        QPushButton[class="primary"] {
            background-color: #6366f1;
            color: white;
        }
        
        QPushButton[class="primary"]:hover {
            background-color: #4f46e5;
        }
        
        QPushButton[class="primary"]:pressed {
            background-color: #4338ca;
        }
        
        /* Inputs */
        QLineEdit, QSpinBox, QComboBox, QPlainTextEdit {
            background-color: #18181b;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 8px;
            color: #f4f4f5;
            selection-background-color: #6366f1;
        }
        
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
            border: 1px solid #6366f1;
        }
        
        /* Labels */
        QLabel {
            color: #f4f4f5;
            background-color: transparent;
        }
        
        QLabel[class="header"] {
            font-size: 24px;
            font-weight: 700;
            color: #f4f4f5;
            margin-bottom: 20px;
        }
        
        QLabel[class="subheader"] {
            font-size: 16px;
            font-weight: 600;
            color: #a1a1aa;
            margin-bottom: 10px;
        }
        
        /* Scrollbars (Webkit style for Qt) */
        QScrollBar:vertical {
            border: none;
            background: #18181b;
            width: 8px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #3f3f46;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        /* Checkboxes */
        QCheckBox {
            spacing: 8px;
            color: #e4e4e7;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #52525b;
            border-radius: 4px;
            background: #18181b;
        }
        QCheckBox::indicator:checked {
            background: #6366f1;
            border-color: #6366f1;
        }
        
        /* Progress Bar */
        QProgressBar {
            border: none;
            background-color: #27272a;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #6366f1;
            border-radius: 4px;
        }
    """
