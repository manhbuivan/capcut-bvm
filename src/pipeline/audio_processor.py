"""Audio processing utilities for pre-processing before ASR."""
import os
from typing import Optional


class AudioProcessor:
    """Pre-processes audio for optimal ASR performance.

    Handles: noise reduction, normalization, silence trimming.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def normalize_audio(self, audio_path: str, output_path: Optional[str] = None) -> str:
        """Normalize audio volume levels.

        Args:
            audio_path: Input audio file path
            output_path: Output path (overwrites input if None)

        Returns:
            Path to normalized audio
        """
        import numpy as np
        import soundfile as sf

        data, sr = sf.read(audio_path)

        # Normalize to [-1, 1] range
        max_val = np.abs(data).max()
        if max_val > 0:
            data = data / max_val * 0.95  # Leave some headroom

        if output_path is None:
            output_path = audio_path

        sf.write(output_path, data, sr)
        return output_path

    def trim_silence(self, audio_path: str, output_path: Optional[str] = None,
                     threshold_db: float = -40.0) -> str:
        """Remove leading and trailing silence from audio.

        Args:
            audio_path: Input audio path
            output_path: Output path (auto if None)
            threshold_db: Silence threshold in dB

        Returns:
            Path to trimmed audio
        """
        import numpy as np
        import soundfile as sf

        data, sr = sf.read(audio_path)

        # Convert threshold to amplitude
        threshold = 10 ** (threshold_db / 20.0)

        # Find non-silent regions
        amplitude = np.abs(data)
        non_silent = amplitude > threshold

        if not non_silent.any():
            # All silence, return as-is
            return audio_path

        # Find first and last non-silent sample
        indices = np.where(non_silent)[0]
        start = max(0, indices[0] - int(sr * 0.1))  # 100ms padding
        end = min(len(data), indices[-1] + int(sr * 0.1))

        trimmed = data[start:end]

        if output_path is None:
            base, ext = os.path.splitext(audio_path)
            output_path = f"{base}_trimmed{ext}"

        sf.write(output_path, trimmed, sr)
        return output_path

    def resample(self, audio_path: str, target_sr: Optional[int] = None,
                 output_path: Optional[str] = None) -> str:
        """Resample audio to target sample rate.

        Args:
            audio_path: Input audio path
            target_sr: Target sample rate (defaults to self.sample_rate)
            output_path: Output path

        Returns:
            Path to resampled audio
        """
        import soundfile as sf
        import numpy as np

        if target_sr is None:
            target_sr = self.sample_rate

        data, sr = sf.read(audio_path)

        if sr == target_sr:
            return audio_path

        # Simple resampling using numpy interpolation
        duration = len(data) / sr
        new_length = int(duration * target_sr)
        indices = np.linspace(0, len(data) - 1, new_length)
        resampled = np.interp(indices, np.arange(len(data)), data)

        if output_path is None:
            base, ext = os.path.splitext(audio_path)
            output_path = f"{base}_{target_sr}hz{ext}"

        sf.write(output_path, resampled, target_sr)
        return output_path
