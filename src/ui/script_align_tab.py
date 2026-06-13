"""Script Alignment tab - ghép kịch bản .txt với audio để tạo SRT."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QProgressBar,
    QComboBox, QFileDialog, QTextEdit, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal


class AlignWorker(QThread):
    """Background thread for forced alignment."""

    progress = Signal(str, float)  # message, percent
    finished = Signal(str)  # output path or error
    error = Signal(str)

    def __init__(self, audio_path, script_path, output_path, model_size, language):
        super().__init__()
        self.audio_path = audio_path
        self.script_path = script_path
        self.output_path = output_path
        self.model_size = model_size
        self.language = language

    def run(self):
        try:
            from ..pipeline.forced_aligner import ForcedAligner

            aligner = ForcedAligner(
                model_size=self.model_size,
                language=self.language
            )
            aligner.set_progress_callback(self._on_progress)

            result = aligner.align(self.audio_path, self.script_path)
            aligner.export_srt(result, self.output_path)

            self.finished.emit(self.output_path)

        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, msg, pct):
        self.progress.emit(msg, pct)


class ScriptAlignTab(QWidget):
    """Tab: Đưa file audio + file kịch bản → tạo SRT có timestamp chính xác."""

    def __init__(self):
        super().__init__()
        self._worker: AlignWorker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Input Files ---
        input_group = QGroupBox("📂 File đầu vào")
        input_layout = QVBoxLayout(input_group)

        # Audio file
        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("🎵 Audio/Video:"))
        self.audio_path_edit = QLineEdit()
        self.audio_path_edit.setPlaceholderText("Chọn file audio hoặc video...")
        self.audio_path_edit.setReadOnly(True)
        audio_row.addWidget(self.audio_path_edit, 1)
        self.btn_browse_audio = QPushButton("Chọn")
        self.btn_browse_audio.clicked.connect(self._browse_audio)
        audio_row.addWidget(self.btn_browse_audio)
        input_layout.addLayout(audio_row)

        # Script file
        script_row = QHBoxLayout()
        script_row.addWidget(QLabel("📝 Kịch bản:"))
        self.script_path_edit = QLineEdit()
        self.script_path_edit.setPlaceholderText("Chọn file .txt kịch bản (mỗi dòng = 1 câu sub)...")
        self.script_path_edit.setReadOnly(True)
        script_row.addWidget(self.script_path_edit, 1)
        self.btn_browse_script = QPushButton("Chọn")
        self.btn_browse_script.clicked.connect(self._browse_script)
        script_row.addWidget(self.btn_browse_script)
        input_layout.addLayout(script_row)

        layout.addWidget(input_group)

        # --- Script Preview ---
        preview_group = QGroupBox("👁 Xem trước kịch bản")
        preview_layout = QVBoxLayout(preview_group)

        self.script_preview = QTextEdit()
        self.script_preview.setReadOnly(True)
        self.script_preview.setMaximumHeight(150)
        self.script_preview.setPlaceholderText(
            "Nội dung kịch bản sẽ hiện ở đây...\n\n"
            "Format file kịch bản:\n"
            "- Mỗi dòng = 1 câu subtitle\n"
            "- Dòng trống sẽ bị bỏ qua\n"
            "- Dòng bắt đầu bằng # là comment"
        )
        preview_layout.addWidget(self.script_preview)

        self.line_count_label = QLabel("")
        self.line_count_label.setObjectName("subtitleLabel")
        preview_layout.addWidget(self.line_count_label)

        layout.addWidget(preview_group)

        # --- Settings ---
        settings_group = QGroupBox("⚙️ Cấu hình")
        settings_layout = QVBoxLayout(settings_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "tiny (nhanh nhất)",
            "small (cân bằng)",
            "medium (chính xác)",
        ])
        self.model_combo.setCurrentIndex(1)
        row1.addWidget(self.model_combo)

        row1.addWidget(QLabel("    Ngôn ngữ:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "vi - Tiếng Việt",
            "en - English",
            "ja - 日本語",
            "zh - 中文",
            "ko - 한국어",
        ])
        row1.addWidget(self.lang_combo)
        settings_layout.addLayout(row1)

        # Output
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Xuất SRT:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Tự động (cùng tên audio + .srt)")
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

        layout.addWidget(progress_group)

        # --- Actions ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_start = QPushButton("▶  Ghép & Tạo SRT")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumWidth(180)
        self.btn_start.clicked.connect(self._start_align)
        btn_row.addWidget(self.btn_start)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file audio/video", "",
            "Media Files (*.mp3 *.wav *.flac *.aac *.ogg *.m4a "
            "*.mp4 *.mkv *.avi *.mov *.webm);;All Files (*)"
        )
        if path:
            self.audio_path_edit.setText(path)

    def _browse_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file kịch bản", "",
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.script_path_edit.setText(path)
            self._preview_script(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu file SRT", "",
            "SRT Files (*.srt);;All Files (*)"
        )
        if path:
            self.output_edit.setText(path)

    def _preview_script(self, path: str):
        """Load and preview script content."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.script_preview.setPlainText(content)

            # Count valid lines
            lines = [l.strip() for l in content.split("\n")
                     if l.strip() and not l.strip().startswith("#")]
            self.line_count_label.setText(f"📌 {len(lines)} câu subtitle")
        except Exception as e:
            self.script_preview.setPlainText(f"Lỗi đọc file: {e}")

    def _get_model_size(self) -> str:
        mapping = {0: "tiny", 1: "small", 2: "medium"}
        return mapping.get(self.model_combo.currentIndex(), "small")

    def _get_language(self) -> str:
        text = self.lang_combo.currentText()
        return text.split(" - ")[0]

    def _get_output_path(self) -> str:
        custom = self.output_edit.text().strip()
        if custom:
            return custom

        audio = self.audio_path_edit.text()
        base = os.path.splitext(audio)[0]
        return f"{base}.srt"

    def _start_align(self):
        audio = self.audio_path_edit.text().strip()
        script = self.script_path_edit.text().strip()

        if not audio:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file audio!")
            return
        if not script:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file kịch bản!")
            return

        output = self._get_output_path()

        # Disable UI
        self.btn_start.setEnabled(False)
        self.progress_bar.setValue(0)

        # Start worker
        self._worker = AlignWorker(
            audio_path=audio,
            script_path=script,
            output_path=output,
            model_size=self._get_model_size(),
            language=self._get_language(),
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
        self.progress_label.setText(f"✅ Đã tạo: {os.path.basename(output_path)}")
        QMessageBox.information(
            self, "Hoàn tất",
            f"Đã tạo file SRT thành công!\n\n{output_path}"
        )

    def _on_error(self, error_msg: str):
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"❌ Lỗi: {error_msg}")
        QMessageBox.critical(self, "Lỗi", f"Không thể tạo SRT:\n{error_msg}")
