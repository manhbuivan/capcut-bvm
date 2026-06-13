"""Timeline alignment utilities for CapCut drafts."""
from typing import List


class TimelineAligner:
    """Aligns and adjusts timeline elements in CapCut drafts.

    Handles: gap removal, segment reordering, overlap fixing.
    """

    def remove_gaps(self, tracks: List[dict]) -> List[dict]:
        """Remove gaps between segments on each track.

        Args:
            tracks: List of track dicts from draft_content

        Returns:
            Tracks with gaps removed
        """
        for track in tracks:
            segments = track.get("segments", [])
            if not segments:
                continue

            # Sort by start time
            segments.sort(key=lambda s: s["target_timerange"]["start"])

            # Close gaps
            current_end = 0
            for seg in segments:
                tr = seg["target_timerange"]
                if tr["start"] > current_end:
                    tr["start"] = current_end
                current_end = tr["start"] + tr["duration"]

            track["segments"] = segments

        return tracks

    def align_subtitles_to_video(self, tracks: List[dict], offset_us: int = 0) -> List[dict]:
        """Shift all subtitle (text) track segments by an offset.

        Args:
            tracks: All tracks from draft
            offset_us: Time offset in microseconds

        Returns:
            Modified tracks
        """
        for track in tracks:
            if track.get("type") != "text":
                continue

            for seg in track.get("segments", []):
                tr = seg["target_timerange"]
                tr["start"] = max(0, tr["start"] + offset_us)

        return tracks

    def get_total_duration(self, tracks: List[dict]) -> int:
        """Get the total duration (end of last segment) across all tracks.

        Returns:
            Duration in microseconds
        """
        max_end = 0
        for track in tracks:
            for seg in track.get("segments", []):
                tr = seg["target_timerange"]
                end = tr["start"] + tr["duration"]
                if end > max_end:
                    max_end = end
        return max_end

    def fix_overlaps(self, tracks: List[dict]) -> List[dict]:
        """Fix overlapping segments within the same track.

        Shortens earlier segments to prevent overlap.

        Args:
            tracks: All tracks

        Returns:
            Tracks with overlaps fixed
        """
        for track in tracks:
            segments = track.get("segments", [])
            if len(segments) < 2:
                continue

            segments.sort(key=lambda s: s["target_timerange"]["start"])

            for i in range(len(segments) - 1):
                current = segments[i]["target_timerange"]
                next_seg = segments[i + 1]["target_timerange"]

                current_end = current["start"] + current["duration"]
                if current_end > next_seg["start"]:
                    # Shorten current segment
                    current["duration"] = next_seg["start"] - current["start"]

            track["segments"] = segments

        return tracks
