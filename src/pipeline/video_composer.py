"""Video Composer: ghép audio + ảnh + subtitle → video hoàn chỉnh bằng FFmpeg.

Workflow:
1. Đưa vào: folder ảnh + file audio + file SRT
2. Tạo slideshow từ ảnh (chia đều hoặc theo timing tùy chỉnh)
3. Ghép audio lên slideshow
4. Burn subtitle vào video
5. Xuất file MP4 hoàn chỉnh
"""
import os
import subprocess
import shutil
from typing import List, Optional, Callable
from dataclasses import dataclass


@dataclass
class ComposerConfig:
    """Cấu hình cho video composer."""
    # Video
    resolution: str = "1920x1080"       # WxH
    fps: int = 30
    video_codec: str = "libx264"
    video_bitrate: str = "4M"
    preset: str = "medium"              # ultrafast, fast, medium, slow

    # Audio
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"

    # Slideshow
    image_duration: float = 0.0         # 0 = tự chia đều theo audio duration
    transition: str = "fade"            # fade, none
    transition_duration: float = 0.5    # Seconds

    # Subtitle
    subtitle_font_size: int = 24
    subtitle_font_color: str = "white"
    subtitle_border_color: str = "black"
    subtitle_border_width: int = 2
    subtitle_position: str = "bottom"   # bottom, top, center
    subtitle_font_name: str = "Arial"

    # Output
    output_format: str = "mp4"


class VideoComposer:
    """Ghép audio + ảnh + subtitle thành video MP4 bằng FFmpeg.

    Usage:
        composer = VideoComposer()
        composer.compose(
            images_folder="/path/to/images",
            audio_path="/path/to/audio.mp3",
            srt_path="/path/to/subtitle.srt",
            output_path="/path/to/output.mp4",
        )
    """

    SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}

    def __init__(self, ffmpeg_path: str = "ffmpeg", config: ComposerConfig = None):
        self.ffmpeg_path = ffmpeg_path
        self.config = config or ComposerConfig()
        self._progress_callback: Optional[Callable] = None
        self._verify_ffmpeg()

    def _verify_ffmpeg(self):
        path = shutil.which(self.ffmpeg_path)
        if path is None:
            raise FileNotFoundError(
                f"FFmpeg không tìm thấy tại '{self.ffmpeg_path}'. "
                "Vui lòng cài FFmpeg hoặc cấu hình đường dẫn."
            )
        self.ffmpeg_path = path

    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set callback: callback(message, percent)"""
        self._progress_callback = callback

    def _report(self, msg: str, pct: float):
        if self._progress_callback:
            self._progress_callback(msg, pct)

    def compose(self, images_folder: str, audio_path: str,
                srt_path: Optional[str] = None,
                output_path: str = "output.mp4") -> str:
        """Ghép ảnh + audio + subtitle → video.

        Args:
            images_folder: Thư mục chứa ảnh (sắp xếp theo tên)
            audio_path: File audio
            srt_path: File subtitle .srt (optional)
            output_path: Đường dẫn video xuất ra

        Returns:
            Đường dẫn file video đã tạo
        """
        # Validate inputs
        if not os.path.isdir(images_folder):
            raise FileNotFoundError(f"Thư mục ảnh không tồn tại: {images_folder}")
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"File audio không tồn tại: {audio_path}")
        if srt_path and not os.path.isfile(srt_path):
            raise FileNotFoundError(f"File SRT không tồn tại: {srt_path}")

        # Get images sorted
        images = self._get_sorted_images(images_folder)
        if not images:
            raise ValueError("Không tìm thấy ảnh nào trong thư mục!")

        # Get audio duration
        self._report("Đang phân tích audio...", 5)
        audio_duration = self._get_duration(audio_path)
        if audio_duration <= 0:
            raise ValueError("Không thể đọc thời lượng audio!")

        # Calculate image duration
        if self.config.image_duration > 0:
            img_duration = self.config.image_duration
        else:
            img_duration = audio_duration / len(images)

        # Create output directory
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Step 1: Create slideshow from images
        self._report(f"Đang tạo slideshow từ {len(images)} ảnh...", 15)
        slideshow_path = output_path + ".slideshow.mp4"
        self._create_slideshow(images, slideshow_path, img_duration, audio_duration)

        # Step 2: Add audio
        self._report("Đang ghép audio...", 50)
        with_audio_path = output_path + ".with_audio.mp4"
        self._add_audio(slideshow_path, audio_path, with_audio_path)

        # Step 3: Burn subtitle (if provided)
        if srt_path:
            self._report("Đang burn subtitle vào video...", 75)
            self._burn_subtitle(with_audio_path, srt_path, output_path)
        else:
            shutil.move(with_audio_path, output_path)

        # Cleanup temp files
        self._report("Đang dọn dẹp...", 95)
        self._cleanup_temp([slideshow_path, with_audio_path])

        self._report("✅ Hoàn tất!", 100)
        return output_path

    def compose_single_image(self, image_path: str, audio_path: str,
                             srt_path: Optional[str] = None,
                             output_path: str = "output.mp4") -> str:
        """Tạo video từ 1 ảnh nền + audio + subtitle.

        Phù hợp cho video podcast, audiobook, nhạc lyric.
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Ảnh không tồn tại: {image_path}")
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio không tồn tại: {audio_path}")

        audio_duration = self._get_duration(audio_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        w, h = self.config.resolution.split("x")

        # Create video from single image + audio
        self._report("Đang tạo video...", 20)

        if srt_path and os.path.isfile(srt_path):
            # Image + audio + subtitle in one command
            srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
            subtitle_filter = (
                f"subtitles='{srt_escaped}':force_style='"
                f"FontSize={self.config.subtitle_font_size},"
                f"FontName={self.config.subtitle_font_name},"
                f"PrimaryColour=&H00FFFFFF,"
                f"OutlineColour=&H00000000,"
                f"BorderStyle=1,"
                f"Outline={self.config.subtitle_border_width},"
                f"Alignment=2'"
            )

            cmd = [
                self.ffmpeg_path,
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                       f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
                       f"{subtitle_filter}",
                "-c:v", self.config.video_codec,
                "-preset", self.config.preset,
                "-b:v", self.config.video_bitrate,
                "-c:a", self.config.audio_codec,
                "-b:a", self.config.audio_bitrate,
                "-shortest",
                "-r", str(self.config.fps),
                "-pix_fmt", "yuv420p",
                "-y",
                output_path
            ]
        else:
            cmd = [
                self.ffmpeg_path,
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                       f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", self.config.video_codec,
                "-preset", self.config.preset,
                "-b:v", self.config.video_bitrate,
                "-c:a", self.config.audio_codec,
                "-b:a", self.config.audio_bitrate,
                "-shortest",
                "-r", str(self.config.fps),
                "-pix_fmt", "yuv420p",
                "-y",
                output_path
            ]

        self._run_ffmpeg(cmd)
        self._report("✅ Hoàn tất!", 100)
        return output_path

    def _get_sorted_images(self, folder: str) -> List[str]:
        """Get images from folder, sorted by name."""
        images = []
        for name in sorted(os.listdir(folder)):
            ext = os.path.splitext(name)[1].lower()
            if ext in self.SUPPORTED_IMAGES:
                images.append(os.path.join(folder, name))
        return images

    def _get_duration(self, file_path: str) -> float:
        """Get media file duration in seconds."""
        ffprobe = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            return float(result.stdout.strip())
        except (ValueError, AttributeError):
            return 0.0

    def _create_slideshow(self, images: List[str], output_path: str,
                          img_duration: float, total_duration: float):
        """Create slideshow video from images using FFmpeg concat."""
        w, h = self.config.resolution.split("x")

        # Create concat file
        concat_file = output_path + ".concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for img_path in images:
                # Escape single quotes for FFmpeg
                escaped = img_path.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")
                f.write(f"duration {img_duration:.3f}\n")
            # Last image needs to be repeated for duration to work
            escaped = images[-1].replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

        # Create slideshow with scaling
        cmd = [
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-vf", (
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1"
            ),
            "-c:v", self.config.video_codec,
            "-preset", self.config.preset,
            "-b:v", self.config.video_bitrate,
            "-r", str(self.config.fps),
            "-pix_fmt", "yuv420p",
            "-t", str(total_duration),
            "-y",
            output_path
        ]

        self._run_ffmpeg(cmd)

        # Cleanup concat file
        if os.path.exists(concat_file):
            os.remove(concat_file)

    def _add_audio(self, video_path: str, audio_path: str, output_path: str):
        """Merge audio track into video."""
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y",
            output_path
        ]
        self._run_ffmpeg(cmd)

    def _burn_subtitle(self, video_path: str, srt_path: str, output_path: str):
        """Burn SRT subtitle into video (hardcoded)."""
        # Escape path for FFmpeg subtitle filter
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        subtitle_filter = (
            f"subtitles='{srt_escaped}':force_style='"
            f"FontSize={self.config.subtitle_font_size},"
            f"FontName={self.config.subtitle_font_name},"
            f"PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,"
            f"BorderStyle=1,"
            f"Outline={self.config.subtitle_border_width},"
            f"Alignment=2'"
        )

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vf", subtitle_filter,
            "-c:v", self.config.video_codec,
            "-preset", self.config.preset,
            "-b:v", self.config.video_bitrate,
            "-c:a", "copy",
            "-y",
            output_path
        ]
        self._run_ffmpeg(cmd)

    def _run_ffmpeg(self, cmd: List[str]):
        """Execute FFmpeg command and handle errors."""
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            error_lines = result.stderr.strip().split("\n")
            # Get last meaningful error lines
            error_msg = "\n".join(error_lines[-5:])
            raise RuntimeError(f"FFmpeg lỗi:\n{error_msg}")

    def _cleanup_temp(self, paths: List[str]):
        """Remove temporary files."""
        for p in paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
