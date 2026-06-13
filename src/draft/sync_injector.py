"""Sync Injector: đồng bộ ảnh + audio + SRT vào CapCut draft.

Inject vào draft_content.json của CapCut:
- Track ảnh: mỗi ảnh = 1 segment, duration = thời lượng audio tương ứng
- Track audio: mỗi audio = 1 segment, nối tiếp nhau
- Track subtitle: mỗi dòng SRT = 1 text segment, đã có timestamp sẵn

Sau khi inject xong, mở CapCut lên sẽ thấy timeline giống screenshot:
  [ảnh 1][ảnh 2][ảnh 3]...
  [audio1][audio2][audio3]...
  [sub 1 ][sub 2 ][sub 3 ]...
"""
import os
import json
import uuid
import shutil
import subprocess
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SRTEntry:
    """Parsed SRT subtitle entry."""
    index: int
    start: float   # seconds
    end: float     # seconds
    text: str


class SyncInjector:
    """Inject synced ảnh + audio + subtitle vào CapCut draft.

    Usage:
        injector = SyncInjector(draft_path="/path/to/draft_folder")
        injector.inject(
            images_folder="/path/to/images",
            audios_folder="/path/to/audios",
            srt_path="/path/to/subtitle.srt",  # optional
        )
        # Mở CapCut → project đã có ảnh+audio+sub sync sẵn trên timeline
    """

    SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    SUPPORTED_AUDIOS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}

    def __init__(self, draft_path: str, ffmpeg_path: str = "ffmpeg"):
        """
        Args:
            draft_path: Đường dẫn thư mục draft CapCut (chứa draft_content.json)
            ffmpeg_path: Đường dẫn ffmpeg (để lấy duration)
        """
        self.draft_path = draft_path
        self.draft_content_path = os.path.join(draft_path, "draft_content.json")
        self.ffmpeg_path = shutil.which(ffmpeg_path) or ffmpeg_path
        self._progress_callback = None

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    def _report(self, msg: str, pct: float):
        if self._progress_callback:
            self._progress_callback(msg, pct)

    def inject(self, images_folder: str, audios_folder: str,
               srt_path: Optional[str] = None,
               script_path: Optional[str] = None) -> str:
        """Inject ảnh + audio + subtitle vào draft CapCut.

        Args:
            images_folder: Thư mục ảnh (sort theo tên)
            audios_folder: Thư mục audio (sort theo tên)
            srt_path: File .srt có sẵn (optional)
            script_path: File .txt kịch bản (optional, sẽ tự tạo SRT)

        Returns:
            Path to modified draft_content.json
        """
        # Load draft
        self._report("Đang đọc draft CapCut...", 5)
        content = self._load_draft()

        # Scan files
        images = self._get_sorted(images_folder, self.SUPPORTED_IMAGES)
        audios = self._get_sorted(audios_folder, self.SUPPORTED_AUDIOS)

        if not images:
            raise ValueError("Không tìm thấy ảnh!")
        if not audios:
            raise ValueError("Không tìm thấy audio!")

        count = min(len(images), len(audios))
        self._report(f"Tìm thấy {count} cặp ảnh+audio", 10)

        # Get audio durations
        self._report("Đang tính thời lượng audio...", 15)
        durations = []
        for audio in audios[:count]:
            dur = self._get_duration(audio)
            if dur <= 0:
                dur = 3.0
            durations.append(dur)

        # Parse SRT hoặc tạo từ script
        srt_entries = []
        if srt_path and os.path.isfile(srt_path):
            self._report("Đang đọc file SRT...", 20)
            srt_entries = self._parse_srt(srt_path)
        elif script_path and os.path.isfile(script_path):
            self._report("Đang tạo SRT từ kịch bản...", 20)
            srt_entries = self._script_to_srt(script_path, durations)

        # Build timeline
        self._report("Đang xây dựng timeline...", 30)

        # Clear existing tracks (optional - để user quyết định)
        # content = self._clear_tracks(content)

        # Inject image track
        self._report("Đang inject ảnh vào timeline...", 40)
        content = self._inject_image_track(content, images[:count], durations)

        # Inject audio track
        self._report("Đang inject audio vào timeline...", 60)
        content = self._inject_audio_track(content, audios[:count], durations)

        # Inject subtitle track
        if srt_entries:
            self._report("Đang inject subtitle vào timeline...", 80)
            content = self._inject_subtitle_track(content, srt_entries)

        # Save draft
        self._report("Đang lưu draft...", 90)
        self._save_draft(content)

        self._report("✅ Hoàn tất! Mở CapCut để xem kết quả.", 100)
        return self.draft_content_path

    def _inject_image_track(self, content: dict, images: List[str],
                            durations: List[float]) -> dict:
        """Inject ảnh vào video track."""
        materials = content.setdefault("materials", {})
        videos = materials.setdefault("videos", [])
        tracks = content.setdefault("tracks", [])

        # Create image track
        track = {
            "id": str(uuid.uuid4()),
            "type": "video",
            "attribute": 0,
            "segments": [],
        }

        cumulative_us = 0
        for i, (img_path, duration) in enumerate(zip(images, durations)):
            duration_us = int(duration * 1_000_000)

            # Material
            mat_id = str(uuid.uuid4())
            material = {
                "id": mat_id,
                "type": "photo",
                "path": img_path,
                "category_name": "photo",
                "width": 1920,
                "height": 1080,
                "duration": duration_us,
            }
            videos.append(material)

            # Segment on track
            segment = {
                "id": str(uuid.uuid4()),
                "material_id": mat_id,
                "source_timerange": {
                    "start": 0,
                    "duration": duration_us,
                },
                "target_timerange": {
                    "start": cumulative_us,
                    "duration": duration_us,
                },
                "extra_material_refs": [],
            }
            track["segments"].append(segment)
            cumulative_us += duration_us

        tracks.append(track)
        return content

    def _inject_audio_track(self, content: dict, audios: List[str],
                            durations: List[float]) -> dict:
        """Inject audio vào audio track."""
        materials = content.setdefault("materials", {})
        audio_materials = materials.setdefault("audios", [])
        tracks = content.setdefault("tracks", [])

        track = {
            "id": str(uuid.uuid4()),
            "type": "audio",
            "attribute": 0,
            "segments": [],
        }

        cumulative_us = 0
        for i, (audio_path, duration) in enumerate(zip(audios, durations)):
            duration_us = int(duration * 1_000_000)

            mat_id = str(uuid.uuid4())
            material = {
                "id": mat_id,
                "type": "audio",
                "path": audio_path,
                "category_name": "audio",
                "duration": duration_us,
            }
            audio_materials.append(material)

            segment = {
                "id": str(uuid.uuid4()),
                "material_id": mat_id,
                "source_timerange": {
                    "start": 0,
                    "duration": duration_us,
                },
                "target_timerange": {
                    "start": cumulative_us,
                    "duration": duration_us,
                },
                "extra_material_refs": [],
            }
            track["segments"].append(segment)
            cumulative_us += duration_us

        tracks.append(track)
        return content

    def _inject_subtitle_track(self, content: dict,
                               entries: List[SRTEntry]) -> dict:
        """Inject subtitle vào text track."""
        materials = content.setdefault("materials", {})
        texts = materials.setdefault("texts", [])
        tracks = content.setdefault("tracks", [])

        track = {
            "id": str(uuid.uuid4()),
            "type": "text",
            "attribute": 0,
            "segments": [],
        }

        for entry in entries:
            start_us = int(entry.start * 1_000_000)
            duration_us = int((entry.end - entry.start) * 1_000_000)

            mat_id = str(uuid.uuid4())
            text_material = {
                "id": mat_id,
                "type": "text",
                "content": entry.text,
                "font_size": 7.0,
                "font_color": [1.0, 1.0, 1.0],
                "font_bold": True,
                "background_color": [0.0, 0.0, 0.0, 0.6],
                "alignment": 1,
            }
            texts.append(text_material)

            segment = {
                "id": str(uuid.uuid4()),
                "material_id": mat_id,
                "source_timerange": {
                    "start": 0,
                    "duration": duration_us,
                },
                "target_timerange": {
                    "start": start_us,
                    "duration": duration_us,
                },
            }
            track["segments"].append(segment)

        tracks.append(track)
        return content

    def _script_to_srt(self, script_path: str, durations: List[float]) -> List[SRTEntry]:
        """Tạo SRT entries từ file kịch bản + duration audio."""
        with open(script_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

        entries = []
        cumulative = 0.0
        count = min(len(lines), len(durations))

        for i in range(count):
            entries.append(SRTEntry(
                index=i + 1,
                start=cumulative,
                end=cumulative + durations[i],
                text=lines[i],
            ))
            cumulative += durations[i]

        return entries

    def _parse_srt(self, srt_path: str) -> List[SRTEntry]:
        """Parse file .srt thành list entries."""
        entries = []
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = content.strip().split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue

            try:
                index = int(lines[0].strip())
                time_parts = lines[1].split(" --> ")
                start = self._parse_srt_time(time_parts[0].strip())
                end = self._parse_srt_time(time_parts[1].strip())
                text = "\n".join(lines[2:])

                entries.append(SRTEntry(index=index, start=start, end=end, text=text))
            except (ValueError, IndexError):
                continue

        return entries

    def _parse_srt_time(self, time_str: str) -> float:
        """Parse SRT timestamp (HH:MM:SS,mmm) → seconds."""
        time_str = time_str.replace(",", ".")
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def _get_sorted(self, folder: str, extensions: set) -> List[str]:
        """Get sorted files by name."""
        files = []
        for name in sorted(os.listdir(folder)):
            ext = os.path.splitext(name)[1].lower()
            if ext in extensions:
                files.append(os.path.join(folder, name))
        return files

    def _get_duration(self, file_path: str) -> float:
        """Get media duration."""
        ffprobe = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
        cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            return float(result.stdout.strip())
        except (ValueError, AttributeError):
            return 0.0

    def _load_draft(self) -> dict:
        """Load draft_content.json."""
        if not os.path.isfile(self.draft_content_path):
            # Tạo draft mới nếu chưa có
            return {
                "id": str(uuid.uuid4()),
                "materials": {"videos": [], "audios": [], "texts": []},
                "tracks": [],
                "canvas_config": {"width": 1920, "height": 1080},
            }

        with open(self.draft_content_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_draft(self, content: dict):
        """Save draft_content.json with backup."""
        # Backup
        if os.path.exists(self.draft_content_path):
            backup = self.draft_content_path + ".bak"
            shutil.copy2(self.draft_content_path, backup)

        os.makedirs(os.path.dirname(self.draft_content_path), exist_ok=True)
        with open(self.draft_content_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, separators=(',', ':'))

    def _clear_tracks(self, content: dict) -> dict:
        """Clear all existing tracks (optional)."""
        content["tracks"] = []
        materials = content.get("materials", {})
        materials["videos"] = []
        materials["audios"] = []
        materials["texts"] = []
        return content
