"""Batch SRT tab - Tạo Subtitle AI hàng loạt (giống giao diện app gốc)."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QGroupBox, QProgressBar,
    QComboBox, QFileDialog, QListWidgetItem, QRadioButton,
    QButtonGroup, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal


class SmartSRTWorker(QThread):
    """Background thread for smart SRT generation."""

    progress = Signal(int, int, str, str)  # index, total, filename, message
    finished = Signal(str)  # summary

    def __init__(self, items, mode, model_size, language, device):
        super().__init__()
        self.items = items  # list of (audio_path, script_path, output_dir)
        self.mode = mode
        self.model_size = model_size
        self.language = language
        self.device = device

    def run(self):
        from ..pipeline.smart_srt_generator import SmartSRTGenerator, SubMode

        mode_map = {"kich_ban": SubMode.KICH_BAN, "chuan": SubMode.CHUAN, "both": SubMode.BOTH}
        sub_mode = mode_map.get(self.mode, SubMode.CHUAN)

        gen = SmartSRTGenerator(
            model_size=self.model_size,
            language=self.language if self.language != "auto" else None,
            device=self.device,
        )

        for audio_path, script_path, output_dir in self.items:
            gen.add_item(audio_path, script_path, output_dir)

        results = gen.run(mode=sub_mode, on_progress=self._on_progress)
        self.finished.emit(f"Hoàn tất: {len(results)} file SRT đã tạo")

    def _on_progress(self, index, total, filename, message):
        self.progress.emit(index, total, filename, message)


class BatchSRTTab(QWidget):
    """Tab Tạo Subtitle AI - hỗ trợ 3 chế độ, chạy hàng loạt."""

    def __init__(self):
        super().__init__()
        self._worker: SmartSRTWorker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- File Đầu Vào ---
        input_group = QGroupBox("📂 File Đầu Vào")
        input_layout = QVBoxLayout(input_group)

        # Media files
        media_row = QHBoxLayout()
        media_row.addWidget(QLabel("Media:"))
        self.media_edit = QLineEdit()
        self.media_edit.setPlaceholderText("Chọn folder audio/video hoặc thêm từng file")
        self.media_edit.setReadOnly(True)
        media_row.addWidget(self.media_edit, 1)
        btn_media_folder = QPushButton("Chọn Folder")
        btn_media_folder.clicked.connect(self._browse_media_folder)
        media_row.addWidget(btn_media_folder)
        btn_media_files = QPushButton("Chọn File")
        btn_media_files.clicked.connect(self._browse_media_files)
        media_row.addWidget(btn_media_files)
        input_layout.addLayout(media_row)

        # Script files (for kịch bản mode)
        script_row = QHBoxLayout()
        script_row.addWidget(QLabel("Kịch Bản:"))
        self.script_edit = QLineEdit()
        self.script_edit.setPlaceholderText("(Tùy chọn) Folder chứa file .txt kịch bản")
        self.script_edit.setReadOnly(True)
        script_row.addWidget(self.script_edit, 1)
        btn_script = QPushButton("Chọn Folder")
        btn_script.clicked.connect(self._browse_script_folder)
        script_row.addWidget(btn_script)
        btn_clear = QPushButton("✕")
        btn_clear.setMaximumWidth(30)
        btn_clear.clicked.connect(lambda: self.script_edit.clear())
        script_row.addWidget(btn_clear)
        input_layout.addLayout(script_row)

        # File list
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        input_layout.addWidget(self.file_list)

        self.file_count = QLabel("0 file")
        self.file_count.setObjectName("subtitleLabel")
        input_layout.addWidget(self.file_count)

        layout.addWidget(input_group)

        # --- Chế Độ Subtitle ---
        mode_group = QGroupBox("🎯 Chế Độ Subtitle")
        mode_layout = QVBoxLayout(mode_group)

        self.mode_group = QButtonGroup(self)

        # Kịch bản
        self.radio_kich_ban = QRadioButton(
            "🔒 Kịch Bản — 1 dòng TXT = 1 sub, timestamp khớp chính xác từng dòng. "
            "Dùng để cắt video theo kịch bản."
        )
        self.mode_group.addButton(self.radio_kich_ban)
        mode_layout.addWidget(self.radio_kich_ban)

        # Chuẩn
        self.radio_chuan = QRadioButton(
            "📝 Chuẩn — Ngắt theo pause + dấu câu (để chạy chữ). "
            "Subtitle mượt, dễ đọc."
        )
        self.radio_chuan.setChecked(True)
        self.mode_group.addButton(self.radio_chuan)
        mode_layout.addWidget(self.radio_chuan)

        # Both
        self.radio_both = QRadioButton(
            "🚀 Tạo cả 2 Mode (Tiết kiệm thời gian) — "
            "Xuất _kich_ban.srt + _chuan.srt"
        )
        self.mode_group.addButton(self.radio_both)
        mode_layout.addWidget(self.radio_both)

        layout.addWidget(mode_group)

        # --- Cấu Hình ---
        config_group = QGroupBox("⚙️ Cấu Hình")
        config_layout = QHBoxLayout(config_group)

        config_layout.addWidget(QLabel("Thiết bị:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "cpu"])
        config_layout.addWidget(self.device_combo)

        config_layout.addWidget(QLabel("  Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "small", "medium", "large-v3"])
        self.model_combo.setCurrentIndex(2)  # medium
        config_layout.addWidget(self.model_combo)

        config_layout.addWidget(QLabel("  Ngôn ngữ:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["auto", "vi", "en", "ja", "zh", "ko"])
        config_layout.addWidget(self.lang_combo)

        config_layout.addStretch()
        layout.addWidget(config_group)

        # --- Progress ---
        progress_group = QGroupBox("📊 Tiến trình")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_label = QLabel("Chờ bắt đầu...")
        self.progress_label.setObjectName("subtitleLabel")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.current_file_label = QLabel("")
        self.current_file_label.setObjectName("subtitleLabel")
        progress_layout.addWidget(self.current_file_label)

        layout.addWidget(progress_group)

        # --- Actions ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_start = QPushButton("▶  Tạo SRT")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumWidth(160)
        self.btn_start.clicked.connect(self._start_batch)
        btn_row.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("⏹  Hủy")
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setMinimumWidth(100)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_cancel)

        layout.addLayout(btn_row)

    # === Browse ===

    def _browse_media_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục media")
        if folder:
            self.media_edit.setText(folder)
            self._load_media_from_folder(folder)

    def _browse_media_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file media", "",
            "Media (*.mp3 *.wav *.flac *.aac *.ogg *.m4a "
            "*.mp4 *.mkv *.avi *.mov *.webm);;All (*)"
        )
        if files:
            self.media_edit.setText(f"{len(files)} file đã chọn")
            self.file_list.clear()
            for f in files:
                name = os.path.basename(f)
                item = QListWidgetItem(f"🎵 {name}")
                item.setData(Qt.UserRole, f)
                self.file_list.addItem(item)
            self.file_count.setText(f"{len(files)} file")

    def _browse_script_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục kịch bản")
        if folder:
            self.script_edit.setText(folder)

    def _load_media_from_folder(self, folder: str):
        exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
                ".mp4", ".mkv", ".avi", ".mov", ".webm"}
        self.file_list.clear()
        files = sorted(f for f in os.listdir(folder)
                       if os.path.splitext(f)[1].lower() in exts)
        for name in files:
            item = QListWidgetItem(f"🎵 {name}")
            item.setData(Qt.UserRole, os.path.join(folder, name))
            self.file_list.addItem(item)
        self.file_count.setText(f"{len(files)} file")

    # === Start/Cancel ===

    def _get_mode(self) -> str:
        if self.radio_kich_ban.isChecked():
            return "kich_ban"
        elif self.radio_both.isChecked():
            return "both"
        return "chuan"

    def _start_batch(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Lỗi", "Chưa thêm file media!")
            return

        # Build items list
        script_folder = self.script_edit.text().strip()
        scripts = []
        if script_folder and os.path.isdir(script_folder):
            scripts = sorted([
                os.path.join(script_folder, f)
                for f in os.listdir(script_folder)
                if f.endswith(".txt")
            ])

        items = []
        for i in range(self.file_list.count()):
            audio_path = self.file_list.item(i).data(Qt.UserRole)
            script_path = scripts[i] if i < len(scripts) else None
            output_dir = os.path.dirname(audio_path)
            items.append((audio_path, script_path, output_dir))

        # Disable UI
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setMaximum(len(items))
        self.progress_bar.setValue(0)

        # Start worker
        self._worker = SmartSRTWorker(
            items=items,
            mode=self._get_mode(),
            model_size=self.model_combo.currentText(),
            language=self.lang_combo.currentText(),
            device=self.device_combo.currentText(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            # Worker doesn't have direct cancel, but we can note it
            self.progress_label.setText("Đang hủy...")

    def _on_progress(self, index: int, total: int, filename: str, message: str):
        self.progress_bar.setValue(index)
        self.progress_label.setText(f"[{index}/{total}] {message}")
        self.current_file_label.setText(filename)

        if index > 0 and index <= self.file_list.count():
            item = self.file_list.item(index - 1)
            if "✅" in message:
                item.setText(f"✅ {os.path.basename(item.data(Qt.UserRole))}")
            elif "❌" in message:
                item.setText(f"❌ {os.path.basename(item.data(Qt.UserRole))}")

    def _on_finished(self, summary: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_label.setText(summary)
        self.current_file_label.setText("")
        QMessageBox.information(self, "Hoàn tất", summary)
