"""Support tab - help and contact information."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt


class SupportTab(QWidget):
    """Tab for support and help information."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # --- Hướng dẫn ---
        guide_group = QGroupBox("📖 Hướng dẫn sử dụng")
        guide_layout = QVBoxLayout(guide_group)

        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setMaximumHeight(200)
        guide_text.setHtml("""
        <h3 style="color: #00d4aa;">Cách sử dụng</h3>
        <ol>
            <li><b>Auto Render:</b> Chọn thư mục chứa draft CapCut → Cấu hình pipeline → Bấm Bắt đầu</li>
            <li><b>Manual FX:</b> Chọn hiệu ứng từ thư viện → Tùy chỉnh thông số → Áp dụng vào draft</li>
        </ol>
        <h3 style="color: #00d4aa;">Yêu cầu hệ thống</h3>
        <ul>
            <li>Windows 10/11 64-bit</li>
            <li>CapCut Desktop đã cài đặt</li>
            <li>RAM tối thiểu 8GB (khuyến nghị 16GB)</li>
            <li>GPU NVIDIA (để tăng tốc ASR)</li>
        </ul>
        <h3 style="color: #00d4aa;">Lưu ý</h3>
        <ul>
            <li>Đảm bảo CapCut đang mở trước khi Auto Render</li>
            <li>Không thao tác chuột/bàn phím khi đang Auto Export</li>
        </ul>
        """)
        guide_layout.addWidget(guide_text)
        layout.addWidget(guide_group)

        # --- Thông tin ---
        info_group = QGroupBox("ℹ️ Thông tin")
        info_layout = QVBoxLayout(info_group)

        info_layout.addWidget(QLabel("Phiên bản: 1.0.0"))
        info_layout.addWidget(QLabel("Python: 3.10 | PySide6 | Faster-Whisper"))
        info_layout.addWidget(QLabel(""))

        contact_label = QLabel("Liên hệ hỗ trợ: (cấu hình trong config.json)")
        contact_label.setObjectName("subtitleLabel")
        info_layout.addWidget(contact_label)

        layout.addWidget(info_group)

        # --- Actions ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_open_config = QPushButton("📂 Mở config.json")
        btn_open_config.clicked.connect(self._open_config)
        btn_row.addWidget(btn_open_config)

        btn_open_logs = QPushButton("📋 Mở Log")
        btn_open_logs.clicked.connect(self._open_logs)
        btn_row.addWidget(btn_open_logs)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _open_config(self):
        import subprocess
        import os
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
        config_path = os.path.abspath(config_path)
        if os.path.exists(config_path):
            subprocess.Popen(["notepad", config_path])

    def _open_logs(self):
        # TODO: Open log file
        pass
