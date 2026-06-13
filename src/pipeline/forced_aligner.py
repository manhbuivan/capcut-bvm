"""Forced Alignment: ghép file kịch bản (.txt) với audio để tạo SRT.

Cách hoạt động:
1. Đọc file kịch bản → tách thành từng câu
2. Chạy ASR trên audio → lấy segments có timestamp
3. Align (ghép) text kịch bản với timestamps từ ASR
4. Xuất SRT với text chính xác từ kịch bản + timing từ audio
"""
import os
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from .asr_handler import ASRHandler, Segment


@dataclass
class AlignedSegment:
    """A script line aligned with audio timing."""
    start: float
    end: float
    text: str
    confidence: float = 1.0  # Alignment confidence (0-1)


class ForcedAligner:
    """Ghép file kịch bản với audio bằng ASR + text matching.

    Workflow:
        aligner = ForcedAligner(model_size="small", language="vi")
        result = aligner.align("audio.mp3", "kich_ban.txt")
        aligner.export_srt(result, "output.srt")
    """

    def __init__(self, model_size: str = "small", language: str = "vi"):
        """
        Args:
            model_size: Whisper model size
            language: Language code
        """
        self.model_size = model_size
        self.language = language
        self.asr = ASRHandler(model_size=model_size, language=language)
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """Set callback: callback(message, percent)"""
        self._progress_callback = callback

    def _report(self, msg: str, pct: float):
        if self._progress_callback:
            self._progress_callback(msg, pct)

    def align(self, audio_path: str, script_path: str) -> List[AlignedSegment]:
        """Ghép audio với file kịch bản.

        Args:
            audio_path: Đường dẫn file audio/video
            script_path: Đường dẫn file kịch bản (.txt), mỗi dòng là 1 câu sub

        Returns:
            List[AlignedSegment] - Các câu kịch bản đã có timestamp
        """
        # Step 1: Đọc kịch bản
        self._report("Đang đọc kịch bản...", 5)
        script_lines = self._read_script(script_path)
        if not script_lines:
            raise ValueError("File kịch bản trống!")

        # Step 2: Trích audio nếu cần
        self._report("Đang chuẩn bị audio...", 10)
        audio_to_process = audio_path
        temp_audio = None

        ext = os.path.splitext(audio_path)[1].lower()
        video_exts = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"}
        if ext in video_exts:
            from ..utils.ffmpeg_handler import FFmpegHandler
            ffmpeg = FFmpegHandler()
            audio_to_process = ffmpeg.extract_audio(audio_path)
            temp_audio = audio_to_process

        # Step 3: ASR để lấy timestamps
        self._report("Đang nhận dạng giọng nói...", 20)
        if not self.asr.is_loaded:
            self._report("Đang tải model AI...", 15)
            self.asr.load_model()

        asr_segments = self.asr.transcribe(audio_to_process)

        self._report("Đang ghép kịch bản với audio...", 70)

        # Step 4: Align kịch bản với ASR segments
        aligned = self._align_segments(script_lines, asr_segments)

        # Cleanup
        if temp_audio and os.path.exists(temp_audio):
            os.remove(temp_audio)

        self._report("Hoàn tất!", 100)
        return aligned

    def _read_script(self, script_path: str) -> List[str]:
        """Đọc file kịch bản, mỗi dòng là 1 câu subtitle.

        Bỏ qua dòng trống và comment (#).
        """
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Không tìm thấy file: {script_path}")

        with open(script_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        result = []
        for line in lines:
            line = line.strip()
            # Bỏ dòng trống và comment
            if line and not line.startswith("#"):
                result.append(line)

        return result

    def _align_segments(self, script_lines: List[str],
                        asr_segments: List[Segment]) -> List[AlignedSegment]:
        """Ghép từng câu kịch bản với timestamp từ ASR.

        Thuật toán:
        - Nối tất cả ASR text thành 1 chuỗi dài
        - Dùng fuzzy matching để tìm vị trí mỗi câu kịch bản trong chuỗi ASR
        - Map vị trí text → timestamp tương ứng
        """
        if not asr_segments:
            # Không nhận diện được gì → chia đều
            return self._fallback_even_split(script_lines, asr_segments)

        # Xây dựng mapping: character position → timestamp
        char_timestamps = self._build_char_timestamp_map(asr_segments)
        full_asr_text = "".join(seg.text for seg in asr_segments)
        full_asr_text_lower = full_asr_text.lower()

        aligned = []
        search_start = 0

        for i, script_line in enumerate(script_lines):
            # Tìm vị trí best match trong ASR text
            match_start, match_end, confidence = self._find_best_match(
                script_line.lower(),
                full_asr_text_lower,
                search_start
            )

            if match_start >= 0:
                # Lấy timestamp từ character position
                start_time = self._get_time_at_position(char_timestamps, match_start)
                end_time = self._get_time_at_position(char_timestamps, match_end)

                aligned.append(AlignedSegment(
                    start=start_time,
                    end=end_time,
                    text=script_line,
                    confidence=confidence,
                ))

                # Di chuyển search pointer
                search_start = match_end
            else:
                # Không tìm thấy match → ước lượng dựa trên vị trí
                estimated = self._estimate_timing(
                    i, len(script_lines), asr_segments, aligned
                )
                aligned.append(AlignedSegment(
                    start=estimated[0],
                    end=estimated[1],
                    text=script_line,
                    confidence=0.3,
                ))

        # Fix overlaps
        aligned = self._fix_overlaps(aligned)

        return aligned

    def _build_char_timestamp_map(self, segments: List[Segment]) -> List[Tuple[int, float]]:
        """Xây map: vị trí character → timestamp.

        Returns: [(char_position, time_seconds), ...]
        """
        mapping = []
        char_pos = 0

        for seg in segments:
            text_len = len(seg.text)
            if text_len == 0:
                continue

            # Linear interpolation within segment
            time_per_char = (seg.end - seg.start) / text_len

            for j in range(text_len):
                t = seg.start + j * time_per_char
                mapping.append((char_pos + j, t))

            char_pos += text_len

        return mapping

    def _get_time_at_position(self, char_map: List[Tuple[int, float]],
                              position: int) -> float:
        """Lấy timestamp tại vị trí character."""
        if not char_map:
            return 0.0

        # Binary search
        lo, hi = 0, len(char_map) - 1

        if position <= char_map[0][0]:
            return char_map[0][1]
        if position >= char_map[-1][0]:
            return char_map[-1][1]

        while lo < hi:
            mid = (lo + hi) // 2
            if char_map[mid][0] < position:
                lo = mid + 1
            else:
                hi = mid

        return char_map[lo][1]

    def _find_best_match(self, query: str, text: str,
                         start_from: int = 0) -> Tuple[int, int, float]:
        """Tìm vị trí khớp nhất của query trong text.

        Returns: (start_pos, end_pos, confidence)
        """
        query_clean = re.sub(r'\s+', '', query)
        text_clean_map = []  # Map cleaned position → original position
        text_clean = []

        for i in range(start_from, len(text)):
            if not text[i].isspace():
                text_clean.append(text[i])
                text_clean_map.append(i)

        text_clean_str = "".join(text_clean)

        if not query_clean or not text_clean_str:
            return (-1, -1, 0.0)

        # Sliding window matching
        best_ratio = 0.0
        best_start = -1
        best_end = -1
        window_size = len(query_clean)

        # Search with some tolerance on window size
        for size_offset in range(0, max(1, window_size // 3)):
            for direction in [0, 1, -1]:
                ws = window_size + size_offset * direction
                if ws <= 0 or ws > len(text_clean_str):
                    continue

                step = max(1, ws // 4)
                for i in range(0, len(text_clean_str) - ws + 1, step):
                    window = text_clean_str[i:i + ws]
                    ratio = SequenceMatcher(None, query_clean, window).ratio()

                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_start = text_clean_map[i] if i < len(text_clean_map) else start_from
                        end_idx = min(i + ws - 1, len(text_clean_map) - 1)
                        best_end = text_clean_map[end_idx] if end_idx < len(text_clean_map) else best_start + ws

                # Early exit if good enough match
                if best_ratio > 0.85:
                    break
            if best_ratio > 0.85:
                break

        # Minimum threshold
        if best_ratio < 0.4:
            return (-1, -1, 0.0)

        return (best_start, best_end, best_ratio)

    def _estimate_timing(self, line_index: int, total_lines: int,
                         asr_segments: List[Segment],
                         already_aligned: List[AlignedSegment]) -> Tuple[float, float]:
        """Ước lượng timing cho câu không match được."""
        if not asr_segments:
            return (0.0, 0.0)

        total_duration = asr_segments[-1].end
        avg_duration = total_duration / total_lines

        if already_aligned:
            # Đặt sau segment cuối đã align
            last = already_aligned[-1]
            start = last.end + 0.1
        else:
            start = line_index * avg_duration

        end = start + avg_duration
        return (round(start, 3), round(min(end, total_duration), 3))

    def _fix_overlaps(self, segments: List[AlignedSegment]) -> List[AlignedSegment]:
        """Fix các segment bị chồng thời gian."""
        for i in range(len(segments) - 1):
            if segments[i].end > segments[i + 1].start:
                # Đặt end = start của segment tiếp theo - gap nhỏ
                segments[i].end = segments[i + 1].start - 0.05
                if segments[i].end <= segments[i].start:
                    segments[i].end = segments[i].start + 0.5

        return segments

    def _fallback_even_split(self, script_lines: List[str],
                             asr_segments: List[Segment]) -> List[AlignedSegment]:
        """Fallback: chia đều thời gian cho từng câu."""
        if asr_segments:
            total = asr_segments[-1].end
        else:
            total = len(script_lines) * 3.0  # Ước 3s/câu

        duration_per_line = total / len(script_lines)

        return [
            AlignedSegment(
                start=round(i * duration_per_line, 3),
                end=round((i + 1) * duration_per_line - 0.1, 3),
                text=line,
                confidence=0.2,
            )
            for i, line in enumerate(script_lines)
        ]

    def export_srt(self, segments: List[AlignedSegment], output_path: str):
        """Xuất kết quả alignment ra file SRT.

        Args:
            segments: Kết quả từ align()
            output_path: Đường dẫn file .srt
        """
        from .srt_exporter import save_srt, Segment as SrtSegment

        # Convert AlignedSegment → Segment
        srt_segments = [
            SrtSegment(start=s.start, end=s.end, text=s.text)
            for s in segments
        ]
        save_srt(srt_segments, output_path)
