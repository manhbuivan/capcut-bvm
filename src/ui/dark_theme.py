"""Dark theme stylesheet for the application."""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #1a1a2e;
}

QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2d2d44;
    border-radius: 8px;
    background-color: #16213e;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #1a1a2e;
    color: #8888aa;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background-color: #16213e;
    color: #00d4aa;
    border-bottom: 2px solid #00d4aa;
}

QTabBar::tab:hover {
    color: #ffffff;
}

QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #1a5276;
}

QPushButton:pressed {
    background-color: #0a2647;
}

QPushButton#primaryBtn {
    background-color: #00d4aa;
    color: #1a1a2e;
}

QPushButton#primaryBtn:hover {
    background-color: #00e6b8;
}

QPushButton#dangerBtn {
    background-color: #e74c3c;
    color: #ffffff;
}

QPushButton#dangerBtn:hover {
    background-color: #ff6b5a;
}

QLabel {
    color: #e0e0e0;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #00d4aa;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #8888aa;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f3460;
    border: 1px solid #2d2d44;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e0e0e0;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00d4aa;
}

QComboBox {
    background-color: #0f3460;
    border: 1px solid #2d2d44;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e0e0e0;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #2d2d44;
    color: #e0e0e0;
    selection-background-color: #0f3460;
}

QProgressBar {
    background-color: #0f3460;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #00d4aa;
    border-radius: 4px;
}

QListWidget {
    background-color: #16213e;
    border: 1px solid #2d2d44;
    border-radius: 6px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #0f3460;
    color: #00d4aa;
}

QListWidget::item:hover {
    background-color: #1a3a5c;
}

QGroupBox {
    border: 1px solid #2d2d44;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #00d4aa;
}

QScrollBar:vertical {
    background-color: #1a1a2e;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2d2d44;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00d4aa;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #2d2d44;
    background-color: #0f3460;
}

QCheckBox::indicator:checked {
    background-color: #00d4aa;
    border-color: #00d4aa;
}

QStatusBar {
    background-color: #0f3460;
    color: #8888aa;
    border-top: 1px solid #2d2d44;
}

QToolTip {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #2d2d44;
    border-radius: 4px;
    padding: 6px;
}
"""
