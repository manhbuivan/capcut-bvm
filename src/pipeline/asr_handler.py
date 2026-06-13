"""ASR (Automatic Speech Recognition) handler using Faster-Whisper."""
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Segment:
    """A transcribed speech segment."""
    start: float   # Start time in seconds
    end: float     # End time in seconds
    text: str      # Transcribed text


class ASRHandler:
    """Speech-to-text using Faster-Whisper for subtitle generation.

    Supports GPU (CUDA) and CPU inference.
    """

    def __init__(self, model_size: str = "small", device: str = "auto",
                 language: Optional[str] = "vi"):
        """
        Args:
            model_size: Whisper model size ('tiny', 'small', 'medium', 'large-v3')
            device: 'cuda', 'cpu', or 'auto'
            language: Language code or None for auto-detect
        """
        self.model_size = model_size
        self.device = device
        self.language = language
        self._model = None

    def load_model(self):
        """Load the Whisper model. Call this before transcribe()."""
        from faster_whisper import WhisperModel

        compute_type = "float16" if self.device != "cpu" else "int8"

        if self.device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        else:
            device = self.device

        if device == "cpu":
            compute_type = "int8"

        self._model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(self, audio_path: str) -> List[Segment]:
        """Transcribe audio file to list of timed segments.

        Args:
            audio_path: Path to audio file (WAV recommended, 16kHz mono)

        Returns:
            List of Segment with start, end, and text
        """
        if self._model is None:
            self.load_model()

        segments_gen, info = self._model.transcribe(
            audio_path,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        segments = []
        for seg in segments_gen:
            text = seg.text.strip()
            if text:
                segments.append(Segment(
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=text,
                ))

        return segments

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
