"""Inject to CapCut tab - đồng bộ ảnh+audio+SRT vào draft CapCut."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QProgressBar,
    QFileDialog, QMessageBox, QLineEdit, QCheckBox
)
from PySide6.QtCore import QThread, Signal


class InjectWorker(QThread):
    """Background thread for injecting into CapCut draft."""

    progress = Signal(str, float)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, draft_path, images_folder, audios_folder, srt_path, script_path, clear_existing):
        super().__init__()
        self.draft_path = draft_path
        self.images_folder = images_folder
        self.audios_folder = audios_folder
        self.srt_path = srt_path
        self.script_path = script_path
        self.clear_existing = clear_existing

    def run(self):
        try:
            from ..draft.sync_injector import SyncInjector

            injector = SyncInjector(draft_path=self.draft_path)
            injector.set_progress_callback(self._on_progress)

            # Clear existing if requested
            if self.clear_existing:
                content = injector._load_draft()
                content = injector._clear_tracks(content)
                injector._save_draft(content)

            result = injector.inject(
                images_folder=self.images_folder,
                audios_folder=self.audios_folder,
                srt_path=self.srt_path if self.srt_path else None,
                script_path=self.script_path if self.script_path else None,
            )
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, msg, pct):
        self.progress.emit(msg, pct)


class InjectCapCutTab(QWidget):
    """Tab: Đồng bộ ảnh + audio + subtitle vào CapCut draft.

    Quy trình:
    1. Chọn thư mục draft CapCut
    2. Chọn folder ảnh + folder audio + file SRT/kịch bản
    3. Bấm Inject → Tool tự sắp xếp lên timeline
    4. Mở CapCut → chỉnh sửa → render
    """

    def __init__(self):
        super().__init__()
        self._worker: InjectWorker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- CapCut Draft ---
        draft_group = QGroupBox("📁 CapCut Draft Project")
        draft_layout = QVBoxLayout(draft_group)

        draft_row = QHBoxLayout()
        draft_row.addWidget(QLabel("Draft:"))
        self.draft_edit = QLineEdit()
        self.draft_edit.setPlaceholderText("Chọn thư mục draft CapCut (chứa draft_content.json)")
        self.draft_edit.setReadOnly(True)
        draft_row.addWidget(self.draft_edit, 1)
        btn_draft = QPushButton("Chọn")
        btn_draft.clicked.connect(self._browse_draft)
        draft_row.addWidget(btn_draft)
        draft_layout.addLayout(draft_row)

        self.draft_info = QLabel(
            "💡 Thường nằm ở: C:/Users/.../AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/..."
        )
        self.draft_info.setObjectName("subtitleLabel")
        self.draft_info.setWordWrap(True)
        draft_layout.addWidget(self.draft_info)

        layout.addWidget(draft_group)

        # --- Input Files ---
        input_group = QGroupBox("📂 Dữ liệu đầu vào (sort theo tên → ghép theo thứ tự)")
        input_layout = QVBoxLayout(input_group)

        # Images
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("🖼️ Ảnh:"))
        self.images_edit = QLineEdit()
        self.images_edit.setPlaceholderText("Folder ảnh (001.jpg, 002.jpg...)")
        self.images_edit.setReadOnly(True)
        row1.addWidget(self.images_edit, 1)
        btn_img = QPushButton("Chọn")
        btn_img.clicked.connect(self._browse_images)
        row1.addWidget(btn_img)
        input_layout.addLayout(row1)

        # Audios
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("🎵 Audio:"))
        self.audios_edit = QLineEdit()
        self.audios_edit.setPlaceholderText("Folder audio (1.mp3, 2.mp3...)")
        self.audios_edit.setReadOnly(True)
        row2.addWidget(self.audios_edit, 1)
        btn_audio = QPushButton("Chọn")
        btn_audio.clicked.connect(self._browse_audios)
        row2.addWidget(btn_audio)
        input_layout.addLayout(row2)

        # SRT
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("📝 SRT:"))
        self.srt_edit = QLineEdit()
        self.srt_edit.setPlaceholderText("(Tùy chọn) File .srt phụ đề")
        self.srt_edit.setReadOnly(True)
        row3.addWidget(self.srt_edit, 1)
        btn_srt = QPushButton("Chọn")
        btn_srt.clicked.connect(self._browse_srt)
        row3.addWidget(btn_srt)
        btn_clear_srt = QPushButton("✕")
        btn_clear_srt.setMaximumWidth(30)
        btn_clear_srt.clicked.connect(lambda: self.srt_edit.clear())
        row3.addWidget(btn_clear_srt)
        input_layout.addLayout(row3)

        # Or script
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("    hoặc TXT:"))
        self.script_edit = QLineEdit()
        self.script_edit.setPlaceholderText("(Tùy chọn) File .txt kịch bản (mỗi dòng = 1 sub)")
        self.script_edit.setReadOnly(True)
        row4.addWidget(self.script_edit, 1)
        btn_script = QPushButton("Chọn")
        btn_script.clicked.connect(self._browse_script)
        row4.addWidget(btn_script)
        btn_clear_script = QPushButton("✕")
        btn_clear_script.setMaximumWidth(30)
        btn_clear_script.clicked.connect(lambda: self.script_edit.clear())
        row4.addWidget(btn_clear_script)
        input_layout.addLayout(row4)

        layout.addWidget(input_group)

        # --- Options ---
        options_group = QGroupBox("⚙️ Tùy chọn")
        options_layout = QVBoxLayout(options_group)

        self.chk_clear = QCheckBox("Xóa timeline cũ trước khi inject (khuyến nghị cho draft mới)")
        self.chk_clear.setChecked(True)
        options_layout.addWidget(self.chk_clear)

        layout.addWidget(options_group)

        # --- Progress ---
        self.progress_label = QLabel("Chờ bắt đầu...")
        self.progress_label.setObjectName("subtitleLabel")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # --- Actions ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_inject = QPushButton("🚀  Inject vào CapCut")
        self.btn_inject.setObjectName("primaryBtn")
        self.btn_inject.setMinimumWidth(200)
        self.btn_inject.clicked.connect(self._start_inject)
        btn_row.addWidget(self.btn_inject)

        layout.addLayout(btn_row)
        layout.addStretch()

    # === Browse ===

    def _browse_draft(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục Draft CapCut")
        if folder:
            # Verify it's a draft folder
            if os.path.isfile(os.path.join(folder, "draft_content.json")):
                self.draft_edit.setText(folder)
                self.draft_info.setText(f"✅ Tìm thấy draft_content.json")
            else:
                self.draft_edit.setText(folder)
                self.draft_info.setText("⚠️ Không tìm thấy draft_content.json — sẽ tạo mới")

    def _browse_images(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if folder:
            self.images_edit.setText(folder)

    def _browse_audios(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục audio")
        if folder:
            self.audios_edit.setText(folder)

    def _browse_srt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file SRT", "", "SRT (*.srt);;All (*)")
        if path:
            self.srt_edit.setText(path)

    def _browse_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file kịch bản", "", "Text (*.txt);;All (*)")
        if path:
            self.script_edit.setText(path)

    # === Inject ===

    def _start_inject(self):
        draft_path = self.draft_edit.text().strip()
        images_folder = self.images_edit.text().strip()
        audios_folder = self.audios_edit.text().strip()
        srt_path = self.srt_edit.text().strip()
        script_path = self.script_edit.text().strip()

        if not draft_path:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn thư mục draft CapCut!")
            return
        if not images_folder:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn thư mục ảnh!")
            return
        if not audios_folder:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn thư mục audio!")
            return

        self.btn_inject.setEnabled(False)
        self.progress_bar.setValue(0)

        self._worker = InjectWorker(
            draft_path=draft_path,
            images_folder=images_folder,
            audios_folder=audios_folder,
            srt_path=srt_path or None,
            script_path=script_path or None,
            clear_existing=self.chk_clear.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, msg: str, pct: float):
        self.progress_label.setText(msg)
        self.progress_bar.setValue(int(pct))

    def _on_finished(self, path: str):
        self.btn_inject.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label.setText("✅ Inject thành công!")
        QMessageBox.information(
            self, "Hoàn tất",
            "Đã inject vào CapCut draft!\n\n"
            "Bước tiếp:\n"
            "1. Mở CapCut\n"
            "2. Mở project đã inject\n"
            "3. Chỉnh sửa nếu cần\n"
            "4. Export video"
        )

    def _on_error(self, msg: str):
        self.btn_inject.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"❌ Lỗi")
        QMessageBox.critical(self, "Lỗi", msg)
