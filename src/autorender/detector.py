"""CapCut UI state detector."""
import os
from typing import Optional, Tuple
from enum import Enum

from .cv_engine import CVEngine


class CapCutState(Enum):
    """Possible states of CapCut window."""
    UNKNOWN = "unknown"
    HOME = "home"
    EDITOR = "editor"
    EXPORTING = "exporting"
    EXPORT_DONE = "export_done"
    ERROR_POPUP = "error_popup"


class Detector:
    """Detects the current state of CapCut by analyzing its window.

    Uses template images stored in assets/images/ to identify UI states.
    """

    def __init__(self, templates_dir: str = None):
        """
        Args:
            templates_dir: Path to directory containing template images
        """
        if templates_dir is None:
            templates_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "assets", "images"
            )
        self.templates_dir = os.path.abspath(templates_dir)
        self.cv = CVEngine(threshold=0.80)
        self._templates: dict = {}

    def load_templates(self):
        """Load all template images from the templates directory."""
        template_map = {
            "home_ready": "home_ready.png",
            "btn_export": "btn_export.png",
            "btn_start": "btn_start.png",
            "popup_export_check": "popup_export_check.png",
            "rendering_check": "rendering_check.png",
        }

        for key, filename in template_map.items():
            path = os.path.join(self.templates_dir, filename)
            if os.path.isfile(path):
                self._templates[key] = self.cv.load_template(path)

    def detect_state(self) -> CapCutState:
        """Detect current CapCut window state.

        Returns:
            Current state enum
        """
        if not self._templates:
            self.load_templates()

        screen = self.cv.capture_screen()

        # Check for export completion
        if "popup_export_check" in self._templates:
            if self.cv.find_template(screen, self._templates["popup_export_check"]):
                return CapCutState.EXPORT_DONE

        # Check for rendering in progress
        if "rendering_check" in self._templates:
            if self.cv.find_template(screen, self._templates["rendering_check"]):
                return CapCutState.EXPORTING

        # Check for export button (editor state)
        if "btn_export" in self._templates:
            if self.cv.find_template(screen, self._templates["btn_export"]):
                return CapCutState.EDITOR

        # Check for home screen
        if "home_ready" in self._templates:
            if self.cv.find_template(screen, self._templates["home_ready"]):
                return CapCutState.HOME

        return CapCutState.UNKNOWN

    def find_export_button(self) -> Optional[Tuple[int, int]]:
        """Find the Export button position on screen.

        Returns:
            (x, y) position or None
        """
        if "btn_export" not in self._templates:
            return None
        screen = self.cv.capture_screen()
        return self.cv.find_template(screen, self._templates["btn_export"])

    def find_start_button(self) -> Optional[Tuple[int, int]]:
        """Find the Start/Render button position.

        Returns:
            (x, y) position or None
        """
        if "btn_start" not in self._templates:
            return None
        screen = self.cv.capture_screen()
        return self.cv.find_template(screen, self._templates["btn_start"])
