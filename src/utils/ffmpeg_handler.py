"""FFmpeg wrapper for video/audio operations."""
import subprocess
import os
import shutil
from typing import Optional


class FFmpegHandler:
    """Handles FFmpeg operations for audio extraction and video processing."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self._verify_ffmpeg()

    def _verify_ffmpeg(self):
        """Check if ffmpeg is available."""
        path = shutil.which(self.ffmpeg_path)
        if path is None:
            raise FileNotFoundError(
                f"FFmpeg not found at '{self.ffmpeg_path}'. "
                "Please install FFmpeg or set the correct path in config.json"
            )
        self.ffmpeg_path = path

    def extract_audio(self, video_path: str, output_path: Optional[str] = None,
                      sample_rate: int = 16000) -> str:
        """Extract audio from video file as WAV for ASR processing.

        Args:
            video_path: Path to input video
            output_path: Path for output WAV (auto-generated if None)
            sample_rate: Audio sample rate (16000 for Whisper)

        Returns:
            Path to extracted audio file
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_path is None:
            base = os.path.splitext(video_path)[0]
            output_path = f"{base}_audio.wav"

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vn",                    # No video
            "-acodec", "pcm_s16le",   # PCM 16-bit
            "-ar", str(sample_rate),  # Sample rate
            "-ac", "1",               # Mono
            "-y",                     # Overwrite
            output_path
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr[:500]}")

        return output_path

    def get_duration(self, file_path: str) -> float:
        """Get duration of a media file in seconds."""
        cmd = [
            self.ffmpeg_path.replace("ffmpeg", "ffprobe"),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return 0.0

        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    def get_video_info(self, file_path: str) -> dict:
        """Get basic video information (resolution, fps, duration)."""
        cmd = [
            self.ffmpeg_path.replace("ffmpeg", "ffprobe"),
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {}

        import json
        try:
            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]
            fmt = data.get("format", {})

            # Parse frame rate fraction
            fps_str = stream.get("r_frame_rate", "30/1")
            num, den = fps_str.split("/")
            fps = int(num) / int(den) if int(den) != 0 else 30.0

            return {
                "width": stream.get("width", 0),
                "height": stream.get("height", 0),
                "fps": round(fps, 2),
                "duration": float(fmt.get("duration", 0)),
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            return {}
