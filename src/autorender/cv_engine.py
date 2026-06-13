"""Computer Vision engine for CapCut UI detection."""
import numpy as np
from typing import Optional, Tuple


class CVEngine:
    """Detects UI elements on screen using template matching.

    Used to find buttons, popups, and states in CapCut window.
    """

    def __init__(self, threshold: float = 0.85):
        """
        Args:
            threshold: Matching confidence threshold (0-1)
        """
        self.threshold = threshold

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """Capture screen or a region of the screen.

        Args:
            region: (x, y, width, height) or None for full screen

        Returns:
            Screenshot as numpy array (BGR)
        """
        import cv2

        # Platform-specific screen capture
        try:
            # Windows with pywin32 + numpy
            import win32gui
            import win32ui
            import win32con

            if region:
                x, y, w, h = region
            else:
                x, y = 0, 0
                w = win32gui.GetSystemMetrics(win32con.SM_CXSCREEN)
                h = win32gui.GetSystemMetrics(win32con.SM_CYSCREEN)

            hdc = win32gui.GetDC(0)
            dc_obj = win32ui.CreateDCFromHandle(hdc)
            mem_dc = dc_obj.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(dc_obj, w, h)
            mem_dc.SelectObject(bitmap)
            mem_dc.BitBlt((0, 0), (w, h), dc_obj, (x, y), win32con.SRCCOPY)

            bmp_info = bitmap.GetInfo()
            bmp_data = bitmap.GetBitmapBits(True)

            img = np.frombuffer(bmp_data, dtype=np.uint8)
            img = img.reshape((bmp_info['bmHeight'], bmp_info['bmWidth'], 4))
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # Cleanup
            mem_dc.DeleteDC()
            win32gui.DeleteObject(bitmap.GetHandle())
            win32gui.ReleaseDC(0, hdc)

            return img

        except ImportError:
            raise RuntimeError("Screen capture requires Windows with pywin32")

    def find_template(self, screen: np.ndarray, template: np.ndarray) -> Optional[Tuple[int, int]]:
        """Find a template image on screen using template matching.

        Args:
            screen: Screenshot image
            template: Template image to find

        Returns:
            (x, y) center position if found, None otherwise
        """
        import cv2

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.threshold:
            # Return center of matched region
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)

        return None

    def load_template(self, path: str) -> np.ndarray:
        """Load a template image from file.

        Args:
            path: Path to template image (PNG)

        Returns:
            Template as numpy array
        """
        import cv2
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Template not found: {path}")
        return img

    def wait_for_template(self, template: np.ndarray, timeout: float = 30.0,
                          interval: float = 0.5,
                          region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int]]:
        """Wait until a template appears on screen.

        Args:
            template: Template image to wait for
            timeout: Max wait time in seconds
            interval: Check interval in seconds
            region: Screen region to check

        Returns:
            Position if found within timeout, None otherwise
        """
        import time

        start = time.time()
        while time.time() - start < timeout:
            screen = self.capture_screen(region)
            pos = self.find_template(screen, template)
            if pos is not None:
                return pos
            time.sleep(interval)

        return None
