"""State machine for auto render flow control."""
import time
import logging
from typing import Optional, Callable
from enum import Enum

from .detector import Detector, CapCutState
from .session import RenderSession

logger = logging.getLogger(__name__)


class RenderPhase(Enum):
    """Phases of the auto render process."""
    IDLE = "idle"
    WAITING_EDITOR = "waiting_editor"
    CLICKING_EXPORT = "clicking_export"
    WAITING_EXPORT_DIALOG = "waiting_export_dialog"
    CLICKING_START = "clicking_start"
    RENDERING = "rendering"
    EXPORT_COMPLETE = "export_complete"
    ERROR = "error"


class AutoRenderStateMachine:
    """Controls the automated export flow for CapCut.

    Flow: Detect Editor → Click Export → Wait Dialog → Click Start →
          Wait Rendering → Detect Complete → Next job
    """

    def __init__(self, detector: Detector):
        self.detector = detector
        self.phase = RenderPhase.IDLE
        self.session: Optional[RenderSession] = None
        self._running = False
        self._on_progress: Optional[Callable] = None
        self._on_complete: Optional[Callable] = None

    def set_callbacks(self, on_progress: Callable = None,
                      on_complete: Callable = None):
        """Set progress and completion callbacks."""
        self._on_progress = on_progress
        self._on_complete = on_complete

    def start(self, session: RenderSession):
        """Start the auto render state machine.

        Args:
            session: RenderSession with jobs queued
        """
        self.session = session
        self.session.start()
        self._running = True
        self.phase = RenderPhase.WAITING_EDITOR
        logger.info(f"Auto render started with {len(session.jobs)} jobs")

    def stop(self):
        """Stop the state machine."""
        self._running = False
        self.phase = RenderPhase.IDLE
        if self.session:
            self.session.stop()
        logger.info("Auto render stopped")

    def tick(self):
        """Execute one tick of the state machine.

        Call this in a loop (e.g., from a QTimer or thread).
        """
        if not self._running or not self.session:
            return

        state = self.detector.detect_state()

        if self.phase == RenderPhase.WAITING_EDITOR:
            self._handle_waiting_editor(state)

        elif self.phase == RenderPhase.CLICKING_EXPORT:
            self._handle_clicking_export()

        elif self.phase == RenderPhase.WAITING_EXPORT_DIALOG:
            self._handle_waiting_dialog(state)

        elif self.phase == RenderPhase.CLICKING_START:
            self._handle_clicking_start()

        elif self.phase == RenderPhase.RENDERING:
            self._handle_rendering(state)

        elif self.phase == RenderPhase.EXPORT_COMPLETE:
            self._handle_complete()

    def _handle_waiting_editor(self, state: CapCutState):
        if state == CapCutState.EDITOR:
            self.phase = RenderPhase.CLICKING_EXPORT
            self._report("Tìm thấy editor, chuẩn bị export...")

    def _handle_clicking_export(self):
        pos = self.detector.find_export_button()
        if pos:
            self._click(pos)
            self.phase = RenderPhase.WAITING_EXPORT_DIALOG
            self._report("Đã click Export, chờ dialog...")
            time.sleep(1)

    def _handle_waiting_dialog(self, state: CapCutState):
        # Look for the Start button in export dialog
        pos = self.detector.find_start_button()
        if pos:
            self.phase = RenderPhase.CLICKING_START

    def _handle_clicking_start(self):
        pos = self.detector.find_start_button()
        if pos:
            self._click(pos)
            self.phase = RenderPhase.RENDERING
            self._report("Đang render...")
            time.sleep(2)

    def _handle_rendering(self, state: CapCutState):
        if state == CapCutState.EXPORT_DONE:
            self.phase = RenderPhase.EXPORT_COMPLETE
            self._report("Export hoàn tất!")

    def _handle_complete(self):
        if self.session:
            self.session.complete_current()

            if self.session.current_job:
                # More jobs to process
                self.phase = RenderPhase.WAITING_EDITOR
                self._report(f"Chuyển sang job tiếp theo...")
                time.sleep(2)
            else:
                # All done
                self._running = False
                self.phase = RenderPhase.IDLE
                self._report("Tất cả đã hoàn tất!")
                if self._on_complete:
                    self._on_complete()

    def _click(self, pos: tuple):
        """Simulate mouse click at position."""
        try:
            import win32api
            import win32con
            win32api.SetCursorPos(pos)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        except ImportError:
            logger.error("win32api not available - cannot simulate clicks")

    def _report(self, message: str):
        logger.info(message)
        if self._on_progress and self.session:
            self._on_progress(message, self.session.progress_percent)
