"""Text preprocessing for subtitle formatting."""
import re
from typing import List
from .asr_handler import Segment


class TextPreprocessor:
    """Clean and format transcribed text for subtitle display.

    Handles: punctuation, line splitting, character limits.
    """

    MAX_CHARS_PER_LINE = 42  # Standard subtitle line length
    MAX_LINES = 2

    def process_segments(self, segments: List[Segment]) -> List[Segment]:
        """Process all segments: clean text and split long lines.

        Args:
            segments: Raw ASR segments

        Returns:
            Processed segments ready for subtitle injection
        """
        processed = []
        for seg in segments:
            text = self._clean_text(seg.text)
            if not text:
                continue

            # Split long segments into multiple lines
            if len(text) > self.MAX_CHARS_PER_LINE * self.MAX_LINES:
                sub_segs = self._split_segment(seg, text)
                processed.extend(sub_segs)
            else:
                processed.append(Segment(
                    start=seg.start,
                    end=seg.end,
                    text=self._wrap_text(text),
                ))

        return processed

    def _clean_text(self, text: str) -> str:
        """Clean up raw ASR text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove repeated punctuation
        text = re.sub(r'([.!?])\1+', r'\1', text)
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        return text

    def _wrap_text(self, text: str) -> str:
        """Wrap text to fit subtitle constraints."""
        if len(text) <= self.MAX_CHARS_PER_LINE:
            return text

        # Try to split at natural break points
        mid = len(text) // 2
        # Look for space near middle
        best_split = mid
        for offset in range(min(15, mid)):
            if mid + offset < len(text) and text[mid + offset] == ' ':
                best_split = mid + offset
                break
            if mid - offset >= 0 and text[mid - offset] == ' ':
                best_split = mid - offset
                break

        line1 = text[:best_split].strip()
        line2 = text[best_split:].strip()
        return f"{line1}\n{line2}"

    def _split_segment(self, seg: Segment, text: str) -> List[Segment]:
        """Split a long segment into multiple shorter ones."""
        words = text.split()
        total_words = len(words)
        if total_words == 0:
            return []

        # Calculate how many sub-segments needed
        max_chars = self.MAX_CHARS_PER_LINE * self.MAX_LINES
        num_parts = (len(text) // max_chars) + 1

        duration = seg.end - seg.start
        time_per_part = duration / num_parts

        parts = []
        words_per_part = total_words // num_parts

        for i in range(num_parts):
            start_idx = i * words_per_part
            end_idx = (i + 1) * words_per_part if i < num_parts - 1 else total_words
            part_text = ' '.join(words[start_idx:end_idx])

            if part_text.strip():
                parts.append(Segment(
                    start=round(seg.start + i * time_per_part, 3),
                    end=round(seg.start + (i + 1) * time_per_part, 3),
                    text=self._wrap_text(part_text),
                ))

        return parts
