"""Main application window with tab-based layout."""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .dark_theme import DARK_STYLESHEET
from .auto_render_tab import AutoRenderTab
from .batch_srt_tab import BatchSRTTab
from .script_align_tab import ScriptAlignTab
from .video_compose_tab import VideoComposeTab
from .sync_compose_tab import SyncComposeTab
from .manual_fx_tab import ManualFXTab
from .support_tab import SupportTab


class MainWindow(QMainWindow):
    """Main window with dark theme and tabbed interface."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CapCut BVM")
        self.setMinimumSize(900, 620)
        self.resize(1000, 680)
        self.setStyleSheet(DARK_STYLESHEET)

        self._setup_ui()

    def _setup_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header
        header = self._create_header()
        layout.addLayout(header)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Add tabs
        self.auto_render_tab = AutoRenderTab()
        self.batch_srt_tab = BatchSRTTab()
        self.script_align_tab = ScriptAlignTab()
        self.sync_compose_tab = SyncComposeTab()
        self.video_compose_tab = VideoComposeTab()
        self.manual_fx_tab = ManualFXTab()
        self.support_tab = SupportTab()

        self.tabs.addTab(self.sync_compose_tab, "🎬 Sync Video")
        self.tabs.addTab(self.batch_srt_tab, "📝 Batch SRT")
        self.tabs.addTab(self.script_align_tab, "🔗 Ghép kịch bản")
        self.tabs.addTab(self.video_compose_tab, "🎥 Tạo Video")
        self.tabs.addTab(self.auto_render_tab, "⚡ Auto Render")
        self.tabs.addTab(self.manual_fx_tab, "✨ Manual FX")
        self.tabs.addTab(self.support_tab, "💬 Hỗ trợ")

        layout.addWidget(self.tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng")

    def _create_header(self) -> QHBoxLayout:
        header = QHBoxLayout()

        # Title
        title = QLabel("CapCut BVM")
        title.setObjectName("titleLabel")
        header.addWidget(title)

        header.addStretch()

        # Version
        version = QLabel("v1.0.0")
        version.setObjectName("subtitleLabel")
        header.addWidget(version)

        return header
