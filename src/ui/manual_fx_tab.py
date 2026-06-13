"""Manual FX tab - apply effects manually to selected drafts."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QGroupBox, QComboBox,
    QListWidgetItem, QSlider, QSpinBox
)
from PySide6.QtCore import Qt


class ManualFXTab(QWidget):
    """Tab for manually applying effects to CapCut drafts."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Effect Library ---
        fx_group = QGroupBox("🎨 Thư viện hiệu ứng")
        fx_layout = QVBoxLayout(fx_group)

        # Category filter
        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Danh mục:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Tất cả", "Transition", "Text Animation",
            "Color Grading", "Overlay", "Sound FX"
        ])
        cat_row.addWidget(self.category_combo)
        fx_layout.addLayout(cat_row)

        # Effect list
        self.fx_list = QListWidget()
        self._load_sample_effects()
        fx_layout.addWidget(self.fx_list)

        layout.addWidget(fx_group)

        # --- Effect Settings ---
        settings_group = QGroupBox("⚙️ Cài đặt hiệu ứng")
        settings_layout = QVBoxLayout(settings_group)

        # Duration
        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Thời lượng (ms):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(100, 5000)
        self.duration_spin.setValue(500)
        self.duration_spin.setSingleStep(50)
        dur_row.addWidget(self.duration_spin)
        settings_layout.addLayout(dur_row)

        # Intensity
        int_row = QHBoxLayout()
        int_row.addWidget(QLabel("Cường độ:"))
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_slider.setValue(75)
        int_row.addWidget(self.intensity_slider)
        self.intensity_label = QLabel("75%")
        self.intensity_slider.valueChanged.connect(
            lambda v: self.intensity_label.setText(f"{v}%")
        )
        int_row.addWidget(self.intensity_label)
        settings_layout.addLayout(int_row)

        layout.addWidget(settings_group)

        # --- Actions ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_preview = QPushButton("👁  Xem trước")
        self.btn_preview.setMinimumWidth(130)
        btn_row.addWidget(self.btn_preview)

        self.btn_apply = QPushButton("✅  Áp dụng")
        self.btn_apply.setObjectName("primaryBtn")
        self.btn_apply.setMinimumWidth(130)
        btn_row.addWidget(self.btn_apply)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _load_sample_effects(self):
        """Load sample FX entries."""
        effects = [
            "🔄 Fade In/Out",
            "⚡ Glitch Transition",
            "🌈 Color Pop",
            "📝 Typewriter Text",
            "🔊 Bass Drop",
            "✨ Sparkle Overlay",
            "🎞️ Film Grain",
            "💫 Zoom Blur",
        ]
        for fx in effects:
            self.fx_list.addItem(QListWidgetItem(fx))
