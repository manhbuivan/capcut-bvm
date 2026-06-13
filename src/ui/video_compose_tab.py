"""Video Compose tab - ghép audio + ảnh + subtitle → video MP4."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QProgressBar,
    QComboBox, QFileDialog, QMessageBox, QLineEdit,
    QSpinBox, QCheckBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal


class ComposeWorker(QThread):
    """Background thread for video composition."""

    progress = Signal(str, float)  # message, percent
    finished = Signal(str)  # output path
    error = Signal(str)

    def __init__(self, images_folder, audio_path, srt_path, output_path, config):
        super().__init__()
        self.images_folder = images_folder
        self.audio_path = audio_path
        self.srt_path = srt_path
        self.output_path = output_path
        self.config = config

    def run(self):
        try:
            from ..pipeline.video_composer import VideoComposer, ComposerConfig
            config = ComposerConfig(**self.config)
            composer = VideoComposer(config=config)
            composer.set_progress_callback(self._on_progress)

            composer.compose(
                images_folder=self.images_folder,
                audio_path=self.audio_path,
                srt_path=self.srt_path if self.srt_path else None,
                output_path=self.output_path,
            )
            self.finished.emit(self.output_path)

        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, msg, pct):
        self.progress.emit(msg, pct)


class VideoComposeTab(QWidget):
    """Tab: Ghép ảnh + audio + subtitle → video MP4 hoàn chỉnh."""

    def __init__(self):
        super().__init__()
        self._worker: ComposeWorker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Input Files ---
        input_group = QGroupBox("📂 File đầu vào")
        input_layout = QVBoxLayout(input_group)

        # Images folder
        img_row = QHBoxLayout()
        img_row.addWidget(QLabel("🖼️ Thư mục ảnh:"))
        self.images_edit = QLineEdit()
        self.images_edit.setPlaceholderText("Chọn folder chứa ảnh (sắp xếp theo tên)")
        self.images_edit.setReadOnly(True)
        img_row.addWidget(self.images_edit, 1)
        btn_img = QPushButton("Chọn")
        btn_img.clicked.connect(self._browse_images)
        img_row.addWidget(btn_img)
        input_layout.addLayout(img_row)

        # Image preview info
        self.img_info_label = QLabel("")
        self.img_info_label.setObjectName("subtitleLabel")
        input_layout.addWidget(self.img_info_label)

        # Audio file
        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("🎵 Audio:"))
        self.audio_edit = QLineEdit()
        self.audio_edit.setPlaceholderText("Chọn file audio (mp3, wav, ...)")
        self.audio_edit.setReadOnly(True)
        audio_row.addWidget(self.audio_edit, 1)
        btn_audio = QPushButton("Chọn")
        btn_audio.clicked.connect(self._browse_audio)
        audio_row.addWidget(btn_audio)
        input_layout.addLayout(audio_row)

        # SRT file (optional)
        srt_row = QHBoxLayout()
        srt_row.addWidget(QLabel("📝 Subtitle:"))
        self.srt_edit = QLineEdit()
        self.srt_edit.setPlaceholderText("(Tùy chọn) File .srt phụ đề")
        self.srt_edit.setReadOnly(True)
        srt_row.addWidget(self.srt_edit, 1)
        btn_srt = QPushButton("Chọn")
        btn_srt.clicked.connect(self._browse_srt)
        srt_row.addWidget(btn_srt)
        btn_clear_srt = QPushButton("✕")
        btn_clear_srt.setMaximumWidth(30)
        btn_clear_srt.clicked.connect(lambda: self.srt_edit.clear())
        srt_row.addWidget(btn_clear_srt)
        input_layout.addLayout(srt_row)

        layout.addWidget(input_group)

        # --- Video Settings ---
        settings_group = QGroupBox("⚙️ Cấu hình video")
        settings_layout = QVBoxLayout(settings_group)

        # Resolution
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Độ phân giải:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080 (Full HD)",
            "1280x720 (HD)",
            "1080x1920 (Full HD Dọc)",
            "720x1280 (HD Dọc)",
            "3840x2160 (4K)",
        ])
        row1.addWidget(self.resolution_combo)

        row1.addWidget(QLabel("    FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setValue(30)
        row1.addWidget(self.fps_spin)
        settings_layout.addLayout(row1)

        # Quality
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Chất lượng:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast (nhanh, file lớn)",
            "fast (cân bằng)",
            "medium (mặc định)",
            "slow (chất lượng cao, chậm)",
        ])
        self.preset_combo.setCurrentIndex(2)
        row2.addWidget(self.preset_combo)

        row2.addWidget(QLabel("    Bitrate:"))
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["2M", "4M", "6M", "8M", "10M"])
        self.bitrate_combo.setCurrentIndex(1)
        row2.addWidget(self.bitrate_combo)
        settings_layout.addLayout(row2)

        # Subtitle settings
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Cỡ chữ sub:"))
        self.sub_size_spin = QSpinBox()
        self.sub_size_spin.setRange(12, 60)
        self.sub_size_spin.setValue(24)
        row3.addWidget(self.sub_size_spin)

        row3.addWidget(QLabel("    Font:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Arial", "Roboto", "Segoe UI", "Tahoma", "Times New Roman"])
        row3.addWidget(self.font_combo)
        settings_layout.addLayout(row3)

        layout.addWidget(settings_group)

        # --- Output ---
        output_group = QGroupBox("💾 Xuất video")
        output_layout = QVBoxLayout(output_group)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Lưu tại:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Chọn nơi lưu file MP4...")
        out_row.addWidget(self.output_edit, 1)
        btn_output = QPushButton("...")
        btn_output.setMaximumWidth(40)
        btn_output.clicked.connect(self._browse_output)
        out_row.addWidget(btn_output)
        output_layout.addLayout(out_row)

        layout.addWidget(output_group)

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

        # --- Actions ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_compose = QPushButton("🎬  Tạo Video")
        self.btn_compose.setObjectName("primaryBtn")
        self.btn_compose.setMinimumWidth(180)
        self.btn_compose.clicked.connect(self._start_compose)
        btn_row.addWidget(self.btn_compose)

        layout.addLayout(btn_row)

    def _browse_images(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if folder:
            self.images_edit.setText(folder)
            # Count images
            exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            count = sum(1 for f in os.listdir(folder)
                        if os.path.splitext(f)[1].lower() in exts)
            self.img_info_label.setText(f"📌 {count} ảnh tìm thấy")

    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file audio", "",
            "Audio (*.mp3 *.wav *.flac *.aac *.ogg *.m4a);;All (*)"
        )
        if path:
            self.audio_edit.setText(path)

    def _browse_srt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file SRT", "",
            "SRT (*.srt);;All (*)"
        )
        if path:
            self.srt_edit.setText(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu video", "",
            "MP4 (*.mp4);;All (*)"
        )
        if path:
            if not path.endswith(".mp4"):
                path += ".mp4"
            self.output_edit.setText(path)

    def _get_resolution(self) -> str:
        text = self.resolution_combo.currentText()
        return text.split(" ")[0]

    def _get_preset(self) -> str:
        mapping = {0: "ultrafast", 1: "fast", 2: "medium", 3: "slow"}
        return mapping.get(self.preset_combo.currentIndex(), "medium")

    def _start_compose(self):
        images_folder = self.images_edit.text().strip()
        audio_path = self.audio_edit.text().strip()
        srt_path = self.srt_edit.text().strip()
        output_path = self.output_edit.text().strip()

        # Validate
        if not images_folder:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn thư mục ảnh!")
            return
        if not audio_path:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file audio!")
            return
        if not output_path:
            # Auto generate output path
            output_path = os.path.join(
                os.path.dirname(audio_path),
                os.path.splitext(os.path.basename(audio_path))[0] + "_video.mp4"
            )
            self.output_edit.setText(output_path)

        # Build config
        config = {
            "resolution": self._get_resolution(),
            "fps": self.fps_spin.value(),
            "preset": self._get_preset(),
            "video_bitrate": self.bitrate_combo.currentText(),
            "subtitle_font_size": self.sub_size_spin.value(),
            "subtitle_font_name": self.font_combo.currentText(),
        }

        # Disable UI
        self.btn_compose.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Đang bắt đầu...")

        # Start worker
        self._worker = ComposeWorker(
            images_folder=images_folder,
            audio_path=audio_path,
            srt_path=srt_path if srt_path else None,
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
        self.btn_compose.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"✅ Đã tạo: {os.path.basename(output_path)}")

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        QMessageBox.information(
            self, "Hoàn tất",
            f"Video đã tạo thành công!\n\n"
            f"📁 {output_path}\n"
            f"📦 {size_mb:.1f} MB"
        )

    def _on_error(self, error_msg: str):
        self.btn_compose.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"❌ Lỗi")
        QMessageBox.critical(self, "Lỗi", f"Không thể tạo video:\n\n{error_msg}")
