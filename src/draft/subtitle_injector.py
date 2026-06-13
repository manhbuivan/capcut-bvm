"""Inject subtitles into CapCut draft projects."""
import uuid
import time
from typing import List

from ..pipeline.asr_handler import Segment


class SubtitleInjector:
    """Injects subtitle segments into CapCut draft_content.json structure.

    CapCut stores subtitles as text elements on a dedicated track.
    """

    # Default subtitle style
    DEFAULT_STYLE = {
        "font_path": "",
        "font_size": 7.0,
        "font_color": [1.0, 1.0, 1.0],
        "font_bold": True,
        "background_color": [0.0, 0.0, 0.0, 0.6],
        "alignment": 1,  # Center bottom
    }

    def __init__(self, style: dict = None):
        self.style = style or self.DEFAULT_STYLE.copy()

    def inject(self, draft_content: dict, segments: List[Segment]) -> dict:
        """Inject subtitle segments into draft content.

        Args:
            draft_content: Parsed draft_content.json
            segments: List of timed text segments

        Returns:
            Modified draft_content with subtitles added
        """
        if not segments:
            return draft_content

        # Create text materials
        text_materials = self._create_text_materials(segments)

        # Add to materials
        materials = draft_content.setdefault("materials", {})
        texts = materials.setdefault("texts", [])
        texts.extend(text_materials)

        # Create subtitle track
        subtitle_track = self._create_subtitle_track(segments, text_materials)

        # Add track to timeline
        tracks = draft_content.setdefault("tracks", [])
        tracks.append(subtitle_track)

        return draft_content

    def _create_text_materials(self, segments: List[Segment]) -> List[dict]:
        """Create CapCut text material entries for each segment."""
        materials = []
        for seg in segments:
            material = {
                "id": str(uuid.uuid4()),
                "type": "text",
                "content": seg.text,
                "font_size": self.style["font_size"],
                "font_color": self.style["font_color"],
                "font_bold": self.style["font_bold"],
                "background_color": self.style["background_color"],
                "alignment": self.style["alignment"],
            }
            materials.append(material)
        return materials

    def _create_subtitle_track(self, segments: List[Segment],
                               materials: List[dict]) -> dict:
        """Create a timeline track with subtitle segments."""
        track_segments = []

        for seg, mat in zip(segments, materials):
            # CapCut uses microseconds for timing
            start_us = int(seg.start * 1_000_000)
            duration_us = int((seg.end - seg.start) * 1_000_000)

            track_seg = {
                "id": str(uuid.uuid4()),
                "material_id": mat["id"],
                "target_timerange": {
                    "start": start_us,
                    "duration": duration_us,
                },
                "source_timerange": {
                    "start": 0,
                    "duration": duration_us,
                },
            }
            track_segments.append(track_seg)

        return {
            "id": str(uuid.uuid4()),
            "type": "text",
            "attribute": 0,
            "segments": track_segments,
        }

    def remove_existing_subtitles(self, draft_content: dict) -> dict:
        """Remove all existing text tracks from draft.

        Args:
            draft_content: Parsed draft_content.json

        Returns:
            Draft content with text tracks removed
        """
        tracks = draft_content.get("tracks", [])
        draft_content["tracks"] = [
            t for t in tracks if t.get("type") != "text"
        ]

        # Also remove text materials
        materials = draft_content.get("materials", {})
        materials.pop("texts", None)

        return draft_content
