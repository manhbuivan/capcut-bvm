"""Inject media files into CapCut draft projects."""
import uuid
import os
from typing import Optional

from ..utils.ffmpeg_handler import FFmpegHandler


class MediaInjector:
    """Injects video/audio/image files into CapCut draft structure."""

    def __init__(self, ffmpeg: Optional[FFmpegHandler] = None):
        self.ffmpeg = ffmpeg or FFmpegHandler()

    def inject_video(self, draft_content: dict, video_path: str,
                     track_index: int = 0, start_time_us: int = 0) -> dict:
        """Add a video file to the draft.

        Args:
            draft_content: Parsed draft_content.json
            video_path: Path to video file
            track_index: Which video track to add to
            start_time_us: Start position in microseconds

        Returns:
            Modified draft content
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        info = self.ffmpeg.get_video_info(video_path)
        duration_us = int(info.get("duration", 0) * 1_000_000)

        # Create material
        material_id = str(uuid.uuid4())
        material = {
            "id": material_id,
            "type": "video",
            "path": video_path,
            "width": info.get("width", 1920),
            "height": info.get("height", 1080),
            "duration": duration_us,
        }

        # Add to materials
        materials = draft_content.setdefault("materials", {})
        videos = materials.setdefault("videos", [])
        videos.append(material)

        # Add to track
        tracks = draft_content.setdefault("tracks", [])
        video_tracks = [t for t in tracks if t.get("type") == "video"]

        if track_index < len(video_tracks):
            track = video_tracks[track_index]
        else:
            track = {
                "id": str(uuid.uuid4()),
                "type": "video",
                "attribute": 0,
                "segments": [],
            }
            tracks.append(track)

        segment = {
            "id": str(uuid.uuid4()),
            "material_id": material_id,
            "target_timerange": {
                "start": start_time_us,
                "duration": duration_us,
            },
            "source_timerange": {
                "start": 0,
                "duration": duration_us,
            },
        }
        track["segments"].append(segment)

        return draft_content

    def inject_audio(self, draft_content: dict, audio_path: str,
                     start_time_us: int = 0) -> dict:
        """Add an audio file to the draft.

        Args:
            draft_content: Parsed draft_content.json
            audio_path: Path to audio file
            start_time_us: Start position in microseconds

        Returns:
            Modified draft content
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        duration = self.ffmpeg.get_duration(audio_path)
        duration_us = int(duration * 1_000_000)

        material_id = str(uuid.uuid4())
        material = {
            "id": material_id,
            "type": "audio",
            "path": audio_path,
            "duration": duration_us,
        }

        materials = draft_content.setdefault("materials", {})
        audios = materials.setdefault("audios", [])
        audios.append(material)

        # Find or create audio track
        tracks = draft_content.setdefault("tracks", [])
        audio_tracks = [t for t in tracks if t.get("type") == "audio"]

        if audio_tracks:
            track = audio_tracks[0]
        else:
            track = {
                "id": str(uuid.uuid4()),
                "type": "audio",
                "attribute": 0,
                "segments": [],
            }
            tracks.append(track)

        segment = {
            "id": str(uuid.uuid4()),
            "material_id": material_id,
            "target_timerange": {
                "start": start_time_us,
                "duration": duration_us,
            },
            "source_timerange": {
                "start": 0,
                "duration": duration_us,
            },
        }
        track["segments"].append(segment)

        return draft_content
