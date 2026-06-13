"""Batch SRT subtitle file generator."""
import os
from typing import List, Optional
from dataclasses import dataclass
from .asr_handler import Segment


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: List[Segment]) -> str:
    """Convert segments to SRT format string.

    Args:
        segments: List of timed text segments

    Returns:
        SRT formatted string
    """
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_timestamp(seg.start)
        end = _format_timestamp(seg.end)
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg.text)
        lines.append("")  # Blank line separator

    return "\n".join(lines)


def save_srt(segments: List[Segment], output_path: str, encoding: str = "utf-8"):
    """Save segments as .srt file.

    Args:
        segments: Timed text segments
        output_path: Output .srt file path
        encoding: File encoding (default utf-8)
    """
    content = segments_to_srt(segments)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding=encoding) as f:
        f.write(content)


@dataclass
class BatchJob:
    """A single file in a batch SRT job."""
    input_path: str
    output_srt_path: str
    status: str = "pending"  # pending, processing, done, error
    error_msg: str = ""
    segments: List[Segment] = None

    def __post_init__(self):
        if self.segments is None:
            self.segments = []


class BatchSRTExporter:
    """Batch process multiple video/audio files → SRT subtitle files.

    Usage:
        exporter = BatchSRTExporter(model_size="small", language="vi")
        exporter.add_file("/path/to/video1.mp4")
        exporter.add_file("/path/to/video2.mp4")
        exporter.add_folder("/path/to/videos/")
        exporter.run(on_progress=callback)
    """

    SUPPORTED_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
    SUPPORTED_AUDIO = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}

    def __init__(self, model_size: str = "small", language: str = "vi",
                 output_dir: Optional[str] = None):
        """
        Args:
            model_size: Whisper model size
            language: Language code ('vi', 'en', 'ja', 'zh', or None for auto)
            output_dir: Directory for output SRT files (None = same as input)
        """
        self.model_size = model_size
        self.language = language
        self.output_dir = output_dir
        self.jobs: List[BatchJob] = []
        self._running = False
        self._cancelled = False

    @property
    def supported_extensions(self) -> set:
        return self.SUPPORTED_VIDEO | self.SUPPORTED_AUDIO

    def add_file(self, file_path: str, output_path: Optional[str] = None):
        """Add a single file to the batch queue.

        Args:
            file_path: Path to video/audio file
            output_path: Custom output SRT path (auto-generated if None)
        """
        if not os.path.isfile(file_path):
            return

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_extensions:
            return

        if output_path is None:
            output_path = self._generate_output_path(file_path)

        self.jobs.append(BatchJob(input_path=file_path, output_srt_path=output_path))

    def add_files(self, file_paths: List[str]):
        """Add multiple files to batch queue.

        Args:
            file_paths: List of file paths
        """
        for path in file_paths:
            self.add_file(path)

    def add_folder(self, folder_path: str, recursive: bool = False):
        """Add all supported files from a folder.

        Args:
            folder_path: Directory to scan
            recursive: Whether to scan subdirectories
        """
        if not os.path.isdir(folder_path):
            return

        if recursive:
            for root, _, files in os.walk(folder_path):
                for name in sorted(files):
                    self.add_file(os.path.join(root, name))
        else:
            for name in sorted(os.listdir(folder_path)):
                self.add_file(os.path.join(folder_path, name))

    def clear(self):
        """Clear all jobs from queue."""
        self.jobs.clear()

    def cancel(self):
        """Cancel the running batch process."""
        self._cancelled = True

    @property
    def total_jobs(self) -> int:
        return len(self.jobs)

    @property
    def completed_jobs(self) -> int:
        return sum(1 for j in self.jobs if j.status == "done")

    @property
    def failed_jobs(self) -> int:
        return sum(1 for j in self.jobs if j.status == "error")

    def run(self, on_progress=None, on_file_done=None):
        """Run batch SRT generation.

        Args:
            on_progress: Callback(job_index, total, filename, status_msg)
            on_file_done: Callback(job) called after each file completes
        """
        from .asr_handler import ASRHandler
        from .audio_processor import AudioProcessor
        from .text_preprocessor import TextPreprocessor
        from ..utils.ffmpeg_handler import FFmpegHandler

        self._running = True
        self._cancelled = False

        # Initialize components
        asr = ASRHandler(model_size=self.model_size, language=self.language)
        audio_proc = AudioProcessor()
        text_proc = TextPreprocessor()
        ffmpeg = FFmpegHandler()

        # Load model once for all files
        if on_progress:
            on_progress(0, self.total_jobs, "", "Đang tải model AI...")
        asr.load_model()

        for i, job in enumerate(self.jobs):
            if self._cancelled:
                job.status = "cancelled"
                continue

            filename = os.path.basename(job.input_path)
            if on_progress:
                on_progress(i + 1, self.total_jobs, filename, "Đang xử lý...")

            try:
                job.status = "processing"

                # Extract audio if video
                ext = os.path.splitext(job.input_path)[1].lower()
                if ext in self.SUPPORTED_VIDEO:
                    audio_path = ffmpeg.extract_audio(job.input_path)
                    temp_audio = True
                else:
                    audio_path = job.input_path
                    temp_audio = False

                # Normalize audio
                audio_path = audio_proc.normalize_audio(audio_path)

                # Transcribe
                segments = asr.transcribe(audio_path)

                # Process text
                segments = text_proc.process_segments(segments)

                # Save SRT
                save_srt(segments, job.output_srt_path)

                job.segments = segments
                job.status = "done"

                # Cleanup temp audio
                if temp_audio and os.path.exists(audio_path):
                    os.remove(audio_path)

                if on_progress:
                    on_progress(i + 1, self.total_jobs, filename,
                                f"✅ Xong ({len(segments)} segments)")

            except Exception as e:
                job.status = "error"
                job.error_msg = str(e)
                if on_progress:
                    on_progress(i + 1, self.total_jobs, filename, f"❌ Lỗi: {e}")

            if on_file_done:
                on_file_done(job)

        self._running = False

    def _generate_output_path(self, input_path: str) -> str:
        """Generate output SRT path from input file path."""
        base = os.path.splitext(input_path)[0]

        if self.output_dir:
            filename = os.path.basename(base)
            return os.path.join(self.output_dir, f"{filename}.srt")

        return f"{base}.srt"

    def get_summary(self) -> str:
        """Get a summary of batch results."""
        done = self.completed_jobs
        failed = self.failed_jobs
        total = self.total_jobs
        return (
            f"Hoàn tất: {done}/{total} file thành công"
            f"{f', {failed} lỗi' if failed else ''}"
        )
