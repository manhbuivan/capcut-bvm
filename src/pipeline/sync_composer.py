"""Sync Composer: đồng bộ hoàn hảo ảnh + audio + subtitle theo thứ tự.

Logic:
- Folder ảnh: 001.jpg, 002.jpg, 003.jpg ...
- Folder audio: 1.mp3, 2.mp3, 3.mp3 ...
- File kịch bản (txt): mỗi dòng = 1 câu subtitle

Map theo thứ tự:
  001.jpg + 1.mp3 + dòng 1 → đoạn 1 (ảnh hiển thị = thời lượng audio)
  002.jpg + 2.mp3 + dòng 2 → đoạn 2
  ...

Tự động tạo file .srt với timestamp chính xác dựa trên thời lượng audio.
Ghép thành 1 video MP4 hoàn chỉnh.
"""
import os
import subprocess
import shutil
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass


@dataclass
class SyncSegment:
    """Một đoạn đã sync: ảnh + audio + text."""
    index: int
    image_path: str
    audio_path: str
    text: str
    audio_duration: float  # seconds
    start_time: float      # cumulative start time
    end_time: float        # cumulative end time


@dataclass
class SyncConfig:
    """Cấu hình cho sync composer."""
    resolution: str = "1920x1080"
    fps: int = 30
    video_codec: str = "libx264"
    video_bitrate: str = "4M"
    preset: str = "medium"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    subtitle_font_size: int = 24
    subtitle_font_name: str = "Arial"
    subtitle_border_width: int = 2
    # Gap giữa các segment (giây)
    gap_between_segments: float = 0.0


class SyncComposer:
    """Đồng bộ hoàn hảo ảnh + audio + subtitle → video.

    Usage:
        composer = SyncComposer()
        composer.compose(
            images_folder="path/to/images",
            audios_folder="path/to/audios",
            script_path="path/to/kich_ban.txt",  # hoặc None
            output_path="output.mp4",
        )
    """

    SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
    SUPPORTED_AUDIOS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}

    def __init__(self, ffmpeg_path: str = "ffmpeg", config: SyncConfig = None):
        self.ffmpeg_path = ffmpeg_path
        self.config = config or SyncConfig()
        self._progress_callback: Optional[Callable] = None
        self._verify_ffmpeg()

    def _verify_ffmpeg(self):
        path = shutil.which(self.ffmpeg_path)
        if path is None:
            raise FileNotFoundError(
                "FFmpeg không tìm thấy. Vui lòng cài FFmpeg."
            )
        self.ffmpeg_path = path

    def set_progress_callback(self, callback: Callable[[str, float], None]):
        self._progress_callback = callback

    def _report(self, msg: str, pct: float):
        if self._progress_callback:
            self._progress_callback(msg, pct)

    def compose(self, images_folder: str, audios_folder: str,
                script_path: Optional[str] = None,
                srt_path: Optional[str] = None,
                output_path: str = "output.mp4") -> str:
        """Ghép đồng bộ ảnh + audio + subtitle → video.

        Args:
            images_folder: Folder ảnh (sort theo tên)
            audios_folder: Folder audio (sort theo tên)
            script_path: File .txt kịch bản (mỗi dòng = 1 sub). Hoặc None.
            srt_path: File .srt có sẵn (dùng thay script_path). Hoặc None.
            output_path: Đường dẫn video output

        Returns:
            Path video đã tạo
        """
        # Validate
        if not os.path.isdir(images_folder):
            raise FileNotFoundError(f"Thư mục ảnh không tồn tại: {images_folder}")
        if not os.path.isdir(audios_folder):
            raise FileNotFoundError(f"Thư mục audio không tồn tại: {audios_folder}")

        # Scan files
        images = self._get_sorted_files(images_folder, self.SUPPORTED_IMAGES)
        audios = self._get_sorted_files(audios_folder, self.SUPPORTED_AUDIOS)

        if not images:
            raise ValueError("Không tìm thấy ảnh!")
        if not audios:
            raise ValueError("Không tìm thấy audio!")

        # Đọc kịch bản (nếu có)
        script_lines = []
        if script_path and os.path.isfile(script_path):
            script_lines = self._read_script(script_path)

        # Map pairs
        count = min(len(images), len(audios))
        self._report(f"Tìm thấy {count} cặp (ảnh: {len(images)}, audio: {len(audios)})", 5)

        # Lấy duration từng audio
        self._report("Đang phân tích thời lượng audio...", 10)
        segments = self._build_segments(images, audios, script_lines, count)

        total_duration = segments[-1].end_time if segments else 0
        self._report(f"Tổng thời lượng: {total_duration:.1f}s ({count} đoạn)", 15)

        # Tạo SRT từ segments (nếu có text)
        generated_srt = None
        if any(seg.text for seg in segments):
            generated_srt = output_path + ".generated.srt"
            self._generate_srt(segments, generated_srt)
            self._report("Đã tạo file SRT tự động", 20)

        # Dùng SRT được cung cấp hoặc SRT tự tạo
        final_srt = srt_path if (srt_path and os.path.isfile(srt_path)) else generated_srt

        # Tạo từng segment video
        self._report("Đang tạo video từng đoạn...", 25)
        temp_segments = []
        for i, seg in enumerate(segments):
            pct = 25 + (i / len(segments)) * 45
            self._report(f"Đoạn {i+1}/{len(segments)}: {os.path.basename(seg.image_path)}", pct)

            seg_path = output_path + f".seg_{i:04d}.mp4"
            self._create_segment_video(seg.image_path, seg.audio_path, seg_path)
            temp_segments.append(seg_path)

        # Nối segments
        self._report("Đang nối video...", 75)
        merged_path = output_path + ".merged.mp4"
        self._concat_videos(temp_segments, merged_path)

        # Burn subtitle
        if final_srt:
            self._report("Đang burn subtitle...", 85)
            self._burn_subtitle(merged_path, final_srt, output_path)
        else:
            shutil.move(merged_path, output_path)

        # Cleanup
        self._report("Đang dọn dẹp...", 95)
        cleanup = temp_segments + [merged_path]
        if generated_srt:
            cleanup.append(generated_srt)
        self._cleanup(cleanup)

        self._report("✅ Hoàn tất!", 100)
        return output_path

    def _build_segments(self, images: List[str], audios: List[str],
                        script_lines: List[str], count: int) -> List[SyncSegment]:
        """Build segment list with cumulative timing."""
        segments = []
        cumulative_time = 0.0

        for i in range(count):
            duration = self._get_duration(audios[i])
            if duration <= 0:
                duration = 3.0  # Fallback 3s

            text = script_lines[i] if i < len(script_lines) else ""

            seg = SyncSegment(
                index=i,
                image_path=images[i],
                audio_path=audios[i],
                text=text,
                audio_duration=duration,
                start_time=cumulative_time,
                end_time=cumulative_time + duration,
            )
            segments.append(seg)
            cumulative_time += duration + self.config.gap_between_segments

        return segments

    def _generate_srt(self, segments: List[SyncSegment], output_path: str):
        """Tạo file SRT với timestamp dựa trên thời lượng audio."""
        lines = []
        idx = 1
        for seg in segments:
            if not seg.text:
                continue
            start = self._format_srt_time(seg.start_time)
            end = self._format_srt_time(seg.end_time)
            lines.append(f"{idx}")
            lines.append(f"{start} --> {end}")
            lines.append(seg.text)
            lines.append("")
            idx += 1

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _format_srt_time(self, seconds: float) -> str:
        """Convert seconds → SRT timestamp HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _create_segment_video(self, image_path: str, audio_path: str, output_path: str):
        """Tạo 1 đoạn video: 1 ảnh + 1 audio."""
        w, h = self.config.resolution.split("x")

        cmd = [
            self.ffmpeg_path,
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-vf", (
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
            ),
            "-c:v", self.config.video_codec,
            "-preset", self.config.preset,
            "-b:v", self.config.video_bitrate,
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-r", str(self.config.fps),
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-y",
            output_path
        ]
        self._run_ffmpeg(cmd)

    def _concat_videos(self, segments: List[str], output_path: str):
        """Nối nhiều video thành 1."""
        concat_file = output_path + ".list.txt"

        with open(concat_file, "w", encoding="utf-8") as f:
            for seg in segments:
                escaped = seg.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        cmd = [
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-y",
            output_path
        ]
        self._run_ffmpeg(cmd)

        if os.path.exists(concat_file):
            os.remove(concat_file)

    def _burn_subtitle(self, video_path: str, srt_path: str, output_path: str):
        """Burn SRT vào video."""
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

    def _get_sorted_files(self, folder: str, extensions: set) -> List[str]:
        """Sort files by name, filter by extension."""
        files = []
        for name in sorted(os.listdir(folder)):
            ext = os.path.splitext(name)[1].lower()
            if ext in extensions:
                files.append(os.path.join(folder, name))
        return files

    def _read_script(self, path: str) -> List[str]:
        """Đọc file kịch bản, mỗi dòng = 1 câu sub."""
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]

    def _get_duration(self, file_path: str) -> float:
        """Lấy duration file media."""
        ffprobe = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            return float(result.stdout.strip())
        except (ValueError, AttributeError):
            return 0.0

    def _run_ffmpeg(self, cmd: List[str]):
        """Run FFmpeg command."""
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            error_lines = result.stderr.strip().split("\n")
            raise RuntimeError(f"FFmpeg lỗi:\n{''.join(error_lines[-5:])}")

    def _cleanup(self, paths: List[str]):
        """Xóa file tạm."""
        for p in paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    def get_preview_mapping(self, images_folder: str, audios_folder: str,
                            script_path: Optional[str] = None) -> List[dict]:
        """Preview mapping trước khi compose (để hiển thị trên UI).

        Returns:
            List of {"image": name, "audio": name, "text": line, "duration": secs}
        """
        images = self._get_sorted_files(images_folder, self.SUPPORTED_IMAGES)
        audios = self._get_sorted_files(audios_folder, self.SUPPORTED_AUDIOS)

        script_lines = []
        if script_path and os.path.isfile(script_path):
            script_lines = self._read_script(script_path)

        count = min(len(images), len(audios))
        result = []

        for i in range(count):
            duration = self._get_duration(audios[i])
            result.append({
                "image": os.path.basename(images[i]),
                "audio": os.path.basename(audios[i]),
                "text": script_lines[i] if i < len(script_lines) else "(không có)",
                "duration": f"{duration:.1f}s",
            })

        return result
