"""Sync Compose tab - đồng bộ ảnh + audio + subtitle → video."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QProgressBar,
    QComboBox, QFileDialog, QMessageBox, QLineEdit,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal


class SyncWorker(QThread):
    """Background thread for sync composition."""

    progress = Signal(str, float)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, images_folder, audios_folder, script_path, srt_path, output_path, config):
        super().__init__()
        self.images_folder = images_folder
        self.audios_folder = audios_folder
        self.script_path = script_path
        self.srt_path = srt_path
        self.output_path = output_path
        self.config = config

    def run(self):
        try:
            from ..pipeline.sync_composer import SyncComposer, SyncConfig
            config = SyncConfig(**self.config)
            composer = SyncComposer(config=config)
            composer.set_progress_callback(self._on_progress)

            composer.compose(
                images_folder=self.images_folder,
                audios_folder=self.audios_folder,
                script_path=self.script_path,
                srt_path=self.srt_path,
                output_path=self.output_path,
            )
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, msg, pct):
        self.progress.emit(msg, pct)


class SyncComposeTab(QWidget):
    """Tab: Đồng bộ hoàn hảo ảnh + audio + subtitle → video.

    Giống CapCut timeline: mỗi ảnh map 1:1 với audio theo thứ tự,
    subtitle hiển thị đúng thời lượng audio tương ứng.
    """

    def __init__(self):
        super().__init__()
        self._worker: SyncWorker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Input ---
        input_group = QGroupBox("📂 Đầu vào (sort theo tên file → ghép theo thứ tự)")
        input_layout = QVBoxLayout(input_group)

        # Images folder
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("🖼️ Ảnh:"))
        self.images_edit = QLineEdit()
        self.images_edit.setPlaceholderText("Folder ảnh (001.jpg, 002.jpg, 003.jpg...)")
        self.images_edit.setReadOnly(True)
        row1.addWidget(self.images_edit, 1)
        btn_img = QPushButton("Chọn")
        btn_img.clicked.connect(self._browse_images)
        row1.addWidget(btn_img)
        input_layout.addLayout(row1)

        # Audios folder
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("🎵 Audio:"))
        self.audios_edit = QLineEdit()
        self.audios_edit.setPlaceholderText("Folder audio (1.mp3, 2.mp3, 3.mp3...)")
        self.audios_edit.setReadOnly(True)
        row2.addWidget(self.audios_edit, 1)
        btn_audio = QPushButton("Chọn")
        btn_audio.clicked.connect(self._browse_audios)
        row2.addWidget(btn_audio)
        input_layout.addLayout(row2)

        # Script (optional)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("📝 Kịch bản:"))
        self.script_edit = QLineEdit()
        self.script_edit.setPlaceholderText("(Tùy chọn) File .txt - mỗi dòng = 1 sub cho 1 ảnh+audio")
        self.script_edit.setReadOnly(True)
        row3.addWidget(self.script_edit, 1)
        btn_script = QPushButton("Chọn")
        btn_script.clicked.connect(self._browse_script)
        row3.addWidget(btn_script)
        btn_clear = QPushButton("✕")
        btn_clear.setMaximumWidth(30)
        btn_clear.clicked.connect(lambda: self.script_edit.clear())
        row3.addWidget(btn_clear)
        input_layout.addLayout(row3)

        # Or existing SRT
        row3b = QHBoxLayout()
        row3b.addWidget(QLabel("    hoặc SRT:"))
        self.srt_edit = QLineEdit()
        self.srt_edit.setPlaceholderText("(Tùy chọn) File .srt có sẵn")
        self.srt_edit.setReadOnly(True)
        row3b.addWidget(self.srt_edit, 1)
        btn_srt = QPushButton("Chọn")
        btn_srt.clicked.connect(self._browse_srt)
        row3b.addWidget(btn_srt)
        btn_clear_srt = QPushButton("✕")
        btn_clear_srt.setMaximumWidth(30)
        btn_clear_srt.clicked.connect(lambda: self.srt_edit.clear())
        row3b.addWidget(btn_clear_srt)
        input_layout.addLayout(row3b)

        layout.addWidget(input_group)

        # --- Preview Table ---
        preview_group = QGroupBox("👁 Xem trước mapping (ảnh ↔ audio ↔ subtitle)")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["#", "Ảnh", "Audio", "Subtitle"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.preview_table.setMaximumHeight(160)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        preview_layout.addWidget(self.preview_table)

        btn_preview_row = QHBoxLayout()
        self.btn_preview = QPushButton("🔄 Cập nhật preview")
        self.btn_preview.clicked.connect(self._update_preview)
        btn_preview_row.addWidget(self.btn_preview)
        self.preview_info = QLabel("")
        self.preview_info.setObjectName("subtitleLabel")
        btn_preview_row.addWidget(self.preview_info)
        btn_preview_row.addStretch()
        preview_layout.addLayout(btn_preview_row)

        layout.addWidget(preview_group)

        # --- Settings ---
        settings_group = QGroupBox("⚙️ Cấu hình")
        settings_layout = QVBoxLayout(settings_group)

        s_row1 = QHBoxLayout()
        s_row1.addWidget(QLabel("Độ phân giải:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080 (Full HD)",
            "1280x720 (HD)",
            "1080x1920 (Dọc Full HD)",
            "720x1280 (Dọc HD)",
        ])
        s_row1.addWidget(self.resolution_combo)
        s_row1.addWidget(QLabel("  Cỡ sub:"))
        self.sub_size = QSpinBox()
        self.sub_size.setRange(12, 60)
        self.sub_size.setValue(24)
        s_row1.addWidget(self.sub_size)
        s_row1.addWidget(QLabel("  Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["ultrafast", "fast", "medium", "slow"])
        self.preset_combo.setCurrentIndex(2)
        s_row1.addWidget(self.preset_combo)
        settings_layout.addLayout(s_row1)

        layout.addWidget(settings_group)

        # --- Output ---
        out_group = QGroupBox("💾 Xuất video")
        out_layout = QVBoxLayout(out_group)
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Lưu tại:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Tự động hoặc chọn nơi lưu...")
        out_row.addWidget(self.output_edit, 1)
        btn_out = QPushButton("...")
        btn_out.setMaximumWidth(40)
        btn_out.clicked.connect(self._browse_output)
        out_row.addWidget(btn_out)
        out_layout.addLayout(out_row)
        layout.addWidget(out_group)

        # --- Progress ---
        self.progress_label = QLabel("Chờ bắt đầu...")
        self.progress_label.setObjectName("subtitleLabel")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # --- Action ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_start = QPushButton("🎬  Tạo Video")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumWidth(180)
        self.btn_start.clicked.connect(self._start_compose)
        btn_row.addWidget(self.btn_start)
        layout.addLayout(btn_row)

    # === Browse ===

    def _browse_images(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if folder:
            self.images_edit.setText(folder)
            self._update_preview()

    def _browse_audios(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục audio")
        if folder:
            self.audios_edit.setText(folder)
            self._update_preview()

    def _browse_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file kịch bản", "", "Text (*.txt);;All (*)")
        if path:
            self.script_edit.setText(path)
            self._update_preview()

    def _browse_srt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file SRT", "", "SRT (*.srt);;All (*)")
        if path:
            self.srt_edit.setText(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu video", "", "MP4 (*.mp4);;All (*)")
        if path:
            if not path.endswith(".mp4"):
                path += ".mp4"
            self.output_edit.setText(path)

    # === Preview ===

    def _update_preview(self):
        """Load and display the mapping preview."""
        images_folder = self.images_edit.text().strip()
        audios_folder = self.audios_edit.text().strip()
        script_path = self.script_edit.text().strip() or None

        if not images_folder or not audios_folder:
            return

        try:
            from ..pipeline.sync_composer import SyncComposer
            composer = SyncComposer()
            mapping = composer.get_preview_mapping(images_folder, audios_folder, script_path)

            self.preview_table.setRowCount(len(mapping))
            for i, item in enumerate(mapping):
                self.preview_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.preview_table.setItem(i, 1, QTableWidgetItem(f"🖼 {item['image']}"))
                self.preview_table.setItem(i, 2, QTableWidgetItem(f"🎵 {item['audio']} ({item['duration']})"))
                self.preview_table.setItem(i, 3, QTableWidgetItem(item['text']))

            self.preview_info.setText(f"✅ {len(mapping)} đoạn sẽ được ghép")

        except Exception as e:
            self.preview_info.setText(f"⚠️ {e}")

    # === Compose ===

    def _start_compose(self):
        images_folder = self.images_edit.text().strip()
        audios_folder = self.audios_edit.text().strip()
        script_path = self.script_edit.text().strip() or None
        srt_path = self.srt_edit.text().strip() or None
        output_path = self.output_edit.text().strip()

        if not images_folder:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn thư mục ảnh!")
            return
        if not audios_folder:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn thư mục audio!")
            return

        if not output_path:
            output_path = os.path.join(audios_folder, "..", "output_sync_video.mp4")
            output_path = os.path.abspath(output_path)
            self.output_edit.setText(output_path)

        config = {
            "resolution": self.resolution_combo.currentText().split(" ")[0],
            "preset": self.preset_combo.currentText(),
            "subtitle_font_size": self.sub_size.value(),
        }

        self.btn_start.setEnabled(False)
        self.progress_bar.setValue(0)

        self._worker = SyncWorker(
            images_folder=images_folder,
            audios_folder=audios_folder,
            script_path=script_path,
            srt_path=srt_path,
            output_path=output_path,
            config=config,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, msg: str, pct: float):
        self.progress_label.setText(msg)
        self.progress_bar.setValue(int(pct))

    def _on_finished(self, output_path: str):
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(100)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        self.progress_label.setText(f"✅ {os.path.basename(output_path)} ({size_mb:.1f} MB)")
        QMessageBox.information(self, "Hoàn tất", f"Video đã tạo!\n\n{output_path}\n({size_mb:.1f} MB)")

    def _on_error(self, msg: str):
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"❌ Lỗi")
        QMessageBox.critical(self, "Lỗi", msg)
