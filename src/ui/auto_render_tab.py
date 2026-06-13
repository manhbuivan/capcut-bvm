"""Auto Render tab - handles batch rendering automation."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QGroupBox, QProgressBar,
    QComboBox, QFileDialog, QListWidgetItem, QCheckBox
)
from PySide6.QtCore import Qt, Signal


class AutoRenderTab(QWidget):
    """Tab for automated CapCut rendering pipeline."""

    render_started = Signal()
    render_stopped = Signal()

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Project Selection ---
        project_group = QGroupBox("📁 Chọn Project CapCut")
        project_layout = QVBoxLayout(project_group)

        # Folder selector
        folder_row = QHBoxLayout()
        self.folder_label = QLabel("Chưa chọn thư mục...")
        self.folder_label.setObjectName("subtitleLabel")
        folder_row.addWidget(self.folder_label, 1)

        self.btn_browse = QPushButton("Chọn thư mục")
        self.btn_browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.btn_browse)
        project_layout.addLayout(folder_row)

        # Draft list
        self.draft_list = QListWidget()
        self.draft_list.setMaximumHeight(160)
        project_layout.addWidget(self.draft_list)

        layout.addWidget(project_group)

        # --- Pipeline Options ---
        options_group = QGroupBox("⚙️ Cấu hình Pipeline")
        options_layout = QVBoxLayout(options_group)

        # ASR options
        asr_row = QHBoxLayout()
        asr_row.addWidget(QLabel("Model nhận dạng giọng nói:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["faster-whisper-small", "faster-whisper-medium"])
        asr_row.addWidget(self.model_combo)
        options_layout.addLayout(asr_row)

        # Language
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Ngôn ngữ:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Tiếng Việt", "English", "日本語", "中文", "Auto Detect"])
        lang_row.addWidget(self.lang_combo)
        options_layout.addLayout(lang_row)

        # Checkboxes
        self.chk_subtitle = QCheckBox("Tạo phụ đề tự động (ASR)")
        self.chk_subtitle.setChecked(True)
        options_layout.addWidget(self.chk_subtitle)

        self.chk_auto_export = QCheckBox("Tự động Export sau khi inject")
        self.chk_auto_export.setChecked(True)
        options_layout.addWidget(self.chk_auto_export)

        layout.addWidget(options_group)

        # --- Progress ---
        progress_group = QGroupBox("📊 Tiến trình")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_label = QLabel("Chờ bắt đầu...")
        self.progress_label.setObjectName("subtitleLabel")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_group)

        # --- Action Buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_start = QPushButton("▶  Bắt đầu")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumWidth(140)
        self.btn_start.clicked.connect(self._start_render)
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹  Dừng")
        self.btn_stop.setObjectName("dangerBtn")
        self.btn_stop.setMinimumWidth(140)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_render)
        btn_row.addWidget(self.btn_stop)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục CapCut Drafts")
        if folder:
            self.folder_label.setText(folder)
            self._load_drafts(folder)

    def _load_drafts(self, folder: str):
        """Scan folder for CapCut draft projects."""
        import os
        self.draft_list.clear()
        try:
            for name in sorted(os.listdir(folder)):
                draft_path = os.path.join(folder, name, "draft_content.json")
                if os.path.isfile(draft_path):
                    item = QListWidgetItem(f"📂 {name}")
                    item.setData(Qt.UserRole, os.path.join(folder, name))
                    self.draft_list.addItem(item)
        except OSError:
            pass

        if self.draft_list.count() == 0:
            self.draft_list.addItem("Không tìm thấy draft nào")

    def _start_render(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_label.setText("Đang xử lý...")
        self.progress_bar.setValue(0)
        self.render_started.emit()
        # TODO: Start pipeline in background thread

    def _stop_render(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_label.setText("Đã dừng")
        self.render_stopped.emit()
        # TODO: Stop background thread
