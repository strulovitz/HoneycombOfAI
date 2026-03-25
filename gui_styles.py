"""
HoneycombOfAI — Bee-Themed Stylesheet
Dark background with honey-gold accents. Consistent across all widgets.
"""

# Bee-themed color palette
COLORS = {
    "bg_dark": "#1a1a2e",          # Deep dark blue-black
    "bg_panel": "#16213e",         # Panel background
    "bg_card": "#1f2b47",          # Card/section background
    "bg_input": "#0f1829",         # Input field background
    "honey": "#f4a900",            # Primary honey gold
    "honey_light": "#ffc940",      # Light honey (hover)
    "honey_dark": "#c48800",       # Dark honey (pressed)
    "amber": "#ff8c00",            # Amber accent
    "text": "#e8e8e8",             # Primary text
    "text_dim": "#8899aa",         # Dimmed text
    "text_bright": "#ffffff",      # Bright text
    "success": "#4caf50",          # Green
    "warning": "#ff9800",          # Orange
    "error": "#f44336",            # Red
    "border": "#2a3a5c",          # Border color
    "border_active": "#f4a900",    # Active border (honey)
    "scrollbar": "#2a3a5c",        # Scrollbar track
    "scrollbar_thumb": "#3a4a6c",  # Scrollbar thumb
}

STYLESHEET = f"""
/* ===== Global ===== */
QMainWindow, QDialog {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text']};
}}

QWidget {{
    color: {COLORS['text']};
    font-family: "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
    font-size: 13px;
}}

/* ===== Labels ===== */
QLabel {{
    color: {COLORS['text']};
    background: transparent;
}}

QLabel[class="title"] {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['honey']};
}}

QLabel[class="subtitle"] {{
    font-size: 15px;
    color: {COLORS['text_dim']};
}}

QLabel[class="stat-value"] {{
    font-size: 28px;
    font-weight: bold;
    color: {COLORS['honey']};
}}

QLabel[class="stat-label"] {{
    font-size: 11px;
    color: {COLORS['text_dim']};
    text-transform: uppercase;
}}

QLabel[class="status-idle"] {{
    font-size: 16px;
    font-weight: bold;
    color: {COLORS['text_dim']};
}}

QLabel[class="status-active"] {{
    font-size: 16px;
    font-weight: bold;
    color: {COLORS['success']};
}}

QLabel[class="status-error"] {{
    font-size: 16px;
    font-weight: bold;
    color: {COLORS['error']};
}}

/* ===== Buttons ===== */
QPushButton {{
    background-color: {COLORS['honey']};
    color: {COLORS['bg_dark']};
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {COLORS['honey_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['honey_dark']};
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_dim']};
}}

QPushButton[class="danger"] {{
    background-color: {COLORS['error']};
    color: white;
}}

QPushButton[class="danger"]:hover {{
    background-color: #e53935;
}}

QPushButton[class="secondary"] {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
}}

QPushButton[class="secondary"]:hover {{
    border-color: {COLORS['honey']};
    color: {COLORS['honey']};
}}

/* ===== Input Fields ===== */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    min-height: 20px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['honey']};
}}

QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", "Ubuntu Mono", monospace;
    font-size: 12px;
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS['honey']};
}}

/* ===== Combo Box ===== */
QComboBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 20px;
    font-size: 13px;
}}

QComboBox:hover {{
    border-color: {COLORS['honey']};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['honey']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['honey']};
    selection-color: {COLORS['bg_dark']};
}}

/* ===== Group Box ===== */
QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 20px;
    font-weight: bold;
    font-size: 13px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    color: {COLORS['honey']};
}}

/* ===== Tab Widget ===== */
QTabWidget::pane {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_dim']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 20px;
    margin-right: 2px;
    font-size: 13px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['honey']};
    border-color: {COLORS['border']};
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text']};
}}

/* ===== Progress Bar ===== */
QProgressBar {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['text']};
    font-size: 11px;
    min-height: 18px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['honey']};
    border-radius: 3px;
}}

/* ===== Scroll Bar ===== */
QScrollBar:vertical {{
    background-color: {COLORS['scrollbar']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['scrollbar_thumb']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['honey']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {COLORS['scrollbar']};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['scrollbar_thumb']};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['honey']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ===== Table / Tree / List ===== */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    gridline-color: {COLORS['border']};
    alternate-background-color: {COLORS['bg_card']};
}}

QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 4px 8px;
}}

QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {COLORS['honey']};
    color: {COLORS['bg_dark']};
}}

QHeaderView::section {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['honey']};
    border: 1px solid {COLORS['border']};
    padding: 6px 8px;
    font-weight: bold;
    font-size: 12px;
}}

/* ===== Slider ===== */
QSlider::groove:horizontal {{
    background: {COLORS['bg_input']};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {COLORS['honey']};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {COLORS['honey_light']};
}}

/* ===== Status Bar ===== */
QStatusBar {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text_dim']};
    border-top: 1px solid {COLORS['border']};
    font-size: 12px;
}}

/* ===== Menu Bar ===== */
QMenuBar {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text']};
    border-bottom: 1px solid {COLORS['border']};
}}

QMenuBar::item:selected {{
    background-color: {COLORS['honey']};
    color: {COLORS['bg_dark']};
}}

QMenu {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
}}

QMenu::item:selected {{
    background-color: {COLORS['honey']};
    color: {COLORS['bg_dark']};
}}

/* ===== Splitter ===== */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:hover {{
    background-color: {COLORS['honey']};
}}

/* ===== Tooltip ===== */
QToolTip {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['honey']};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ===== Check Box ===== */
QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['bg_input']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['honey']};
    border-color: {COLORS['honey']};
}}

/* ===== Radio Button ===== */
QRadioButton {{
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
    background-color: {COLORS['bg_input']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['honey']};
    border-color: {COLORS['honey']};
}}
"""
