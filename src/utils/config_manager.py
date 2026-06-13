"""Application configuration manager."""
import json
import os
from typing import Any


CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
CONFIG_FILE = os.path.abspath(CONFIG_FILE)

_DEFAULT_CONFIG = {
    "capcut_drafts_path": "",
    "whisper_model": "small",
    "language": "vi",
    "output_dir": "",
    "ffmpeg_path": "ffmpeg",
}


class ConfigManager:
    """Simple JSON-based config manager."""

    def __init__(self, path: str = CONFIG_FILE):
        self.path = path
        self._data: dict = {}
        self.load()

    def load(self):
        if os.path.isfile(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = _DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    @property
    def data(self) -> dict:
        return self._data.copy()
