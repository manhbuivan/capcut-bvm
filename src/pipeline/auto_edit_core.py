"""Core auto-edit pipeline orchestrator."""
import os
from typing import List, Optional, Callable

from .asr_handler import ASRHandler, Segment
from .audio_processor import AudioProcessor
from .text_preprocessor import TextPreprocessor
from ..utils.ffmpeg_handler import FFmpegHandler


class AutoEditCore:
    """Orchestrates the full auto-edit pipeline:
    Video → Extract Audio → ASR → Process Text → Ready for injection.
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Application config dict with model settings
        """
        self.config = config
        self.ffmpeg = FFmpegHandler(config.get("ffmpeg_path", "ffmpeg"))
        self.audio_processor = AudioProcessor()
        self.text_preprocessor = TextPreprocessor()
        self.asr = ASRHandler(
            model_size=config.get("whisper_model", "small"),
            language=config.get("language", "vi"),
        )
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set callback for progress updates: callback(message, percent)."""
        self._progress_callback = callback

    def _report(self, message: str, percent: float):
        if self._progress_callback:
            self._progress_callback(message, percent)

    def process_video(self, video_path: str) -> List[Segment]:
        """Run full pipeline on a video file.

        Args:
            video_path: Path to input video

        Returns:
            List of processed subtitle segments
        """
        self._report("Đang trích xuất âm thanh...", 10)

        # Step 1: Extract audio
        audio_path = self.ffmpeg.extract_audio(video_path)

        self._report("Đang chuẩn hóa âm thanh...", 20)

        # Step 2: Pre-process audio
        audio_path = self.audio_processor.normalize_audio(audio_path)

        self._report("Đang nhận dạng giọng nói...", 30)

        # Step 3: ASR
        if not self.asr.is_loaded:
            self._report("Đang tải model AI...", 25)
            self.asr.load_model()

        segments = self.asr.transcribe(audio_path)

        self._report("Đang xử lý phụ đề...", 80)

        # Step 4: Post-process text
        segments = self.text_preprocessor.process_segments(segments)

        self._report("Hoàn tất!", 100)

        # Cleanup temp audio
        if os.path.exists(audio_path) and audio_path.endswith("_audio.wav"):
            os.remove(audio_path)

        return segments

    def process_audio_file(self, audio_path: str) -> List[Segment]:
        """Process an audio file directly (skip extraction).

        Args:
            audio_path: Path to audio file

        Returns:
            Processed segments
        """
        self._report("Đang nhận dạng giọng nói...", 30)

        if not self.asr.is_loaded:
            self._report("Đang tải model AI...", 20)
            self.asr.load_model()

        segments = self.asr.transcribe(audio_path)

        self._report("Đang xử lý phụ đề...", 80)
        segments = self.text_preprocessor.process_segments(segments)

        self._report("Hoàn tất!", 100)
        return segments
