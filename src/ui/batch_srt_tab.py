"""Batch SRT generation tab - create multiple .srt files at once."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QGroupBox, QProgressBar,
    QComboBox, QFileDialog, QListWidgetItem, QCheckBox,
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal


class BatchWorker(QThread):
    """Background thread for batch SRT processing."""

    progress = Signal(int, int, str, str)  # index, total, filename, message
    file_done = Signal(object)  # BatchJob
    finished = Signal(str)  # summary message

    def __init__(self, exporter):
        super().__init__()
        self.exporter = exporter

    def run(self):
        self.exporter.run(
            on_progress=self._on_progress,
            on_file_done=self._on_file_done,
        )
        self.finished.emit(self.exporter.get_summary())

    def _on_progress(self, index, total, filename, message):
        self.progress.emit(index, total, filename, message)

    def _on_file_done(self, job):
        self.file_done.emit(job)


class BatchSRTTab(QWidget):
    """Tab for batch generating SRT subtitle files from multiple videos/audio."""

    def __init__(self):
        super().__init__()
        self._worker: BatchWorker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- File Selection ---
        file_group = QGroupBox("📂 Chọn file video/audio")
        file_layout = QVBoxLayout(file_group)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_add_files = QPushButton("➕ Thêm file")
        self.btn_add_files.clicked.connect(self._add_files)
        btn_row.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton("📁 Thêm thư mục")
        self.btn_add_folder.clicked.connect(self._add_folder)
        btn_row.addWidget(self.btn_add_folder)

        self.btn_clear = QPushButton("🗑️ Xóa tất cả")
        self.btn_clear.clicked.connect(self._clear_list)
        btn_row.addWidget(self.btn_clear)

        btn_row.addStretch()

        self.file_count_label = QLabel("0 file")
        self.file_count_label.setObjectName("subtitleLabel")
        btn_row.addWidget(self.file_count_label)

        file_layout.addLayout(btn_row)

        # File list
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(140)
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        file_layout.addWidget(self.file_list)

        layout.addWidget(file_group)

        # --- Settings ---
        settings_group = QGroupBox("⚙️ Cấu hình")
        settings_layout = QVBoxLayout(settings_group)

        # Model
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "tiny (nhanh, kém chính xác)",
            "small (cân bằng)",
            "medium (chính xác hơn)",
            "large-v3 (tốt nhất, chậm)",
        ])
        self.model_combo.setCurrentIndex(1)
        model_row.addWidget(self.model_combo)
        settings_layout.addLayout(model_row)

        # Language
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Ngôn ngữ:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "vi - Tiếng Việt",
            "en - English",
            "ja - 日本語",
            "zh - 中文",
            "ko - 한국어",
            "auto - Tự nhận diện",
        ])
        lang_row.addWidget(self.lang_combo)
        settings_layout.addLayout(lang_row)

        # Output directory
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Thư mục xuất:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Cùng thư mục với file gốc")
        out_row.addWidget(self.output_edit, 1)
        self.btn_browse_output = QPushButton("...")
        self.btn_browse_output.setMaximumWidth(40)
        self.btn_browse_output.clicked.connect(self._browse_output)
        out_row.addWidget(self.btn_browse_output)
        settings_layout.addLayout(out_row)

        layout.addWidget(settings_group)

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
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()

        self.btn_start = QPushButton("▶  Tạo SRT")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumWidth(160)
        self.btn_start.clicked.connect(self._start_batch)
        btn_row2.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("⏹  Hủy")
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setMinimumWidth(120)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_batch)
        btn_row2.addWidget(self.btn_cancel)

        layout.addLayout(btn_row2)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn file video/audio",
            "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.wmv *.webm "
            "*.mp3 *.wav *.flac *.aac *.ogg *.m4a);;All Files (*)"
        )
        for f in files:
            self._add_to_list(f)
        self._update_count()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa media")
        if not folder:
            return

        supported = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm",
                     ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}

        for name in sorted(os.listdir(folder)):
            ext = os.path.splitext(name)[1].lower()
            if ext in supported:
                self._add_to_list(os.path.join(folder, name))

        self._update_count()

    def _add_to_list(self, file_path: str):
        # Check duplicates
        for i in range(self.file_list.count()):
            if self.file_list.item(i).data(Qt.UserRole) == file_path:
                return

        name = os.path.basename(file_path)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        item = QListWidgetItem(f"🎬 {name}  ({size_mb:.1f} MB)")
        item.setData(Qt.UserRole, file_path)
        self.file_list.addItem(item)

    def _clear_list(self):
        self.file_list.clear()
        self._update_count()

    def _update_count(self):
        count = self.file_list.count()
        self.file_count_label.setText(f"{count} file")

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất SRT")
        if folder:
            self.output_edit.setText(folder)

    def _get_model_size(self) -> str:
        mapping = {0: "tiny", 1: "small", 2: "medium", 3: "large-v3"}
        return mapping.get(self.model_combo.currentIndex(), "small")

    def _get_language(self) -> str:
        text = self.lang_combo.currentText()
        lang = text.split(" - ")[0]
        return None if lang == "auto" else lang

    def _start_batch(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Lỗi", "Chưa thêm file nào!")
            return

        from ..pipeline.srt_exporter import BatchSRTExporter

        output_dir = self.output_edit.text().strip() or None
        exporter = BatchSRTExporter(
            model_size=self._get_model_size(),
            language=self._get_language(),
            output_dir=output_dir,
        )

        # Add files from list
        for i in range(self.file_list.count()):
            file_path = self.file_list.item(i).data(Qt.UserRole)
            exporter.add_file(file_path)

        # Disable UI
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_add_files.setEnabled(False)
        self.btn_add_folder.setEnabled(False)
        self.progress_bar.setMaximum(exporter.total_jobs)
        self.progress_bar.setValue(0)

        # Start worker thread
        self._worker = BatchWorker(exporter)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _cancel_batch(self):
        if self._worker and self._worker.exporter:
            self._worker.exporter.cancel()
            self.progress_label.setText("Đang hủy...")

    def _on_progress(self, index: int, total: int, filename: str, message: str):
        self.progress_bar.setValue(index)
        self.progress_label.setText(f"[{index}/{total}] {message}")
        self.current_file_label.setText(filename)

        # Update list item status
        if index > 0 and index <= self.file_list.count():
            item = self.file_list.item(index - 1)
            if "✅" in message:
                item.setText(f"✅ {os.path.basename(item.data(Qt.UserRole))}")
            elif "❌" in message:
                item.setText(f"❌ {os.path.basename(item.data(Qt.UserRole))}")

    def _on_finished(self, summary: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_add_files.setEnabled(True)
        self.btn_add_folder.setEnabled(True)
        self.progress_label.setText(summary)
        self.current_file_label.setText("")

        QMessageBox.information(self, "Hoàn tất", summary)
