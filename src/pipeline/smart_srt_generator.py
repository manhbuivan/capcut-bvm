"""Smart SRT Generator: tạo SRT theo nhiều chế độ.

Chế độ:
1. Kịch Bản: 1 dòng TXT = 1 sub, timestamp khớp chính xác từng dòng.
   Dùng để cắt video theo kịch bản.

2. Chuẩn: Ngắt theo pause + dấu câu (để chạy chữ).
   ASR nhận dạng audio → ngắt câu thông minh theo:
   - Khoảng im lặng (pause > 300ms)
   - Dấu câu (., !, ?, ;, :)
   - Giới hạn ký tự mỗi dòng (tối đa ~42 ký tự)
   Subtitle chạy mượt, dễ đọc.

3. Cả 2: Tạo cả 2 file cùng lúc (_kich_ban.srt + _chuan.srt)
"""
import os
import re
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

from .asr_handler import ASRHandler, Segment
from .srt_exporter import save_srt, segments_to_srt


class SubMode(Enum):
    KICH_BAN = "kich_ban"       # 1 dòng = 1 sub
    CHUAN = "chuan"             # Ngắt pause + dấu câu
    BOTH = "both"               # Cả 2


@dataclass
class BatchItem:
    """Một item trong batch."""
    audio_path: str
    script_path: Optional[str] = None  # File .txt kịch bản (cho mode KICH_BAN)
    output_dir: Optional[str] = None
    status: str = "pending"
    error_msg: str = ""


class SmartSRTGenerator:
    """Tạo SRT hàng loạt với các chế độ thông minh.

    Usage:
        gen = SmartSRTGenerator(model_size="medium", language="vi", device="cuda")
        gen.add_item(audio_path="1.mp3", script_path="kich_ban.txt")
        gen.add_folder(audio_folder="audios/", script_folder="scripts/")
        gen.run(mode=SubMode.CHUAN, on_progress=callback)
    """

    # Punctuation that triggers subtitle break
    BREAK_PUNCTUATION = {'.', '!', '?', ';', ':', '。', '！', '？'}
    # Punctuation that suggests a soft break (prefer but don't force)
    SOFT_BREAK = {',', '，', '、'}

    MAX_CHARS_PER_SUB = 42
    MIN_PAUSE_MS = 300  # Minimum pause to split (milliseconds)

    def __init__(self, model_size: str = "medium", language: Optional[str] = None,
                 device: str = "auto"):
        """
        Args:
            model_size: tiny, small, medium, large-v3
            language: 'vi', 'en', 'ja', 'zh', None=auto
            device: 'cuda', 'cpu', 'auto'
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self.items: List[BatchItem] = []
        self._asr: Optional[ASRHandler] = None
        self._cancelled = False

    def add_item(self, audio_path: str, script_path: Optional[str] = None,
                 output_dir: Optional[str] = None):
        """Thêm 1 file audio vào batch."""
        if os.path.isfile(audio_path):
            self.items.append(BatchItem(
                audio_path=audio_path,
                script_path=script_path,
                output_dir=output_dir,
            ))

    def add_folder(self, audio_folder: str, script_folder: Optional[str] = None,
                   output_dir: Optional[str] = None):
        """Thêm cả folder audio + script vào batch.

        Map audio ↔ script theo thứ tự tên file.
        """
        audio_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma",
                      ".mp4", ".mkv", ".avi", ".mov", ".webm"}
        script_exts = {".txt"}

        audios = sorted([
            os.path.join(audio_folder, f) for f in os.listdir(audio_folder)
            if os.path.splitext(f)[1].lower() in audio_exts
        ])

        scripts = []
        if script_folder and os.path.isdir(script_folder):
            scripts = sorted([
                os.path.join(script_folder, f) for f in os.listdir(script_folder)
                if os.path.splitext(f)[1].lower() in script_exts
            ])

        for i, audio in enumerate(audios):
            script = scripts[i] if i < len(scripts) else None
            self.items.append(BatchItem(
                audio_path=audio,
                script_path=script,
                output_dir=output_dir,
            ))

    def clear(self):
        self.items.clear()

    def cancel(self):
        self._cancelled = True

    def run(self, mode: SubMode = SubMode.CHUAN,
            on_progress: Optional[Callable] = None) -> List[str]:
        """Chạy batch tạo SRT.

        Args:
            mode: Chế độ tạo subtitle
            on_progress: callback(index, total, filename, message)

        Returns:
            List đường dẫn file SRT đã tạo
        """
        self._cancelled = False
        output_files = []

        # Load model
        if on_progress:
            on_progress(0, len(self.items), "", "Đang tải model AI...")
        self._load_model()

        for i, item in enumerate(self.items):
            if self._cancelled:
                item.status = "cancelled"
                continue

            filename = os.path.basename(item.audio_path)
            if on_progress:
                on_progress(i + 1, len(self.items), filename, "Đang xử lý...")

            try:
                item.status = "processing"
                results = self._process_item(item, mode)
                output_files.extend(results)
                item.status = "done"

                if on_progress:
                    on_progress(i + 1, len(self.items), filename,
                                f"✅ Xong ({len(results)} file)")

            except Exception as e:
                item.status = "error"
                item.error_msg = str(e)
                if on_progress:
                    on_progress(i + 1, len(self.items), filename, f"❌ {e}")

        return output_files

    def _load_model(self):
        """Load ASR model."""
        if self._asr is None or not self._asr.is_loaded:
            self._asr = ASRHandler(
                model_size=self.model_size,
                language=self.language,
                device=self.device,
            )
            self._asr.load_model()

    def _process_item(self, item: BatchItem, mode: SubMode) -> List[str]:
        """Process 1 item, return list of output SRT paths."""
        base = os.path.splitext(item.audio_path)[0]
        output_dir = item.output_dir or os.path.dirname(item.audio_path)
        base_name = os.path.splitext(os.path.basename(item.audio_path))[0]

        results = []

        # Always run ASR to get raw segments
        raw_segments = self._asr.transcribe(item.audio_path)

        if mode in (SubMode.KICH_BAN, SubMode.BOTH):
            # Mode Kịch Bản
            srt_path = os.path.join(output_dir, f"{base_name}_kich_ban.srt")
            segments = self._create_kich_ban_srt(raw_segments, item.script_path)
            save_srt(segments, srt_path)
            results.append(srt_path)

        if mode in (SubMode.CHUAN, SubMode.BOTH):
            # Mode Chuẩn
            srt_path = os.path.join(output_dir, f"{base_name}_chuan.srt")
            segments = self._create_chuan_srt(raw_segments)
            save_srt(segments, srt_path)
            results.append(srt_path)

        return results

    # ====== MODE KỊCH BẢN ======

    def _create_kich_ban_srt(self, raw_segments: List[Segment],
                             script_path: Optional[str]) -> List[Segment]:
        """Mode Kịch Bản: 1 dòng kịch bản = 1 sub.

        Dùng ASR để tìm timestamp, nhưng text lấy từ kịch bản.
        """
        if not script_path or not os.path.isfile(script_path):
            # Không có kịch bản → dùng ASR segments gộp thành câu dài
            return self._merge_to_sentences(raw_segments)

        # Đọc kịch bản
        with open(script_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

        if not lines:
            return raw_segments

        # Ghép kịch bản với ASR timing (forced alignment đơn giản)
        return self._align_script_to_audio(lines, raw_segments)

    def _align_script_to_audio(self, script_lines: List[str],
                               asr_segments: List[Segment]) -> List[Segment]:
        """Align kịch bản với timing từ ASR (chia đều theo tỷ lệ text)."""
        if not asr_segments:
            return [Segment(start=i * 3, end=(i + 1) * 3, text=line)
                    for i, line in enumerate(script_lines)]

        total_audio_duration = asr_segments[-1].end
        total_text_len = sum(len(line) for line in script_lines)

        if total_text_len == 0:
            return []

        segments = []
        current_time = asr_segments[0].start

        for line in script_lines:
            # Tỷ lệ thời gian dựa trên độ dài text
            ratio = len(line) / total_text_len
            duration = ratio * total_audio_duration
            end_time = min(current_time + duration, total_audio_duration)

            segments.append(Segment(
                start=round(current_time, 3),
                end=round(end_time, 3),
                text=line,
            ))
            current_time = end_time

        return segments

    def _merge_to_sentences(self, segments: List[Segment]) -> List[Segment]:
        """Gộp ASR segments thành các câu hoàn chỉnh."""
        if not segments:
            return []

        merged = []
        current_text = ""
        current_start = segments[0].start

        for seg in segments:
            current_text += seg.text

            # Check if sentence ends
            if current_text and current_text[-1] in self.BREAK_PUNCTUATION:
                merged.append(Segment(
                    start=current_start,
                    end=seg.end,
                    text=current_text.strip(),
                ))
                current_text = ""
                current_start = seg.end

        # Remaining text
        if current_text.strip():
            merged.append(Segment(
                start=current_start,
                end=segments[-1].end,
                text=current_text.strip(),
            ))

        return merged

    # ====== MODE CHUẨN ======

    def _create_chuan_srt(self, raw_segments: List[Segment]) -> List[Segment]:
        """Mode Chuẩn: ngắt theo pause + dấu câu, tối ưu để chạy chữ.

        Rules:
        - Ngắt tại khoảng im lặng > 300ms
        - Ngắt tại dấu câu (., !, ?, ;)
        - Mỗi sub tối đa ~42 ký tự
        - Dấu phẩy → ngắt nếu đoạn đã dài
        """
        if not raw_segments:
            return []

        result = []
        buffer_text = ""
        buffer_start = raw_segments[0].start
        prev_end = raw_segments[0].start

        for seg in raw_segments:
            # Kiểm tra pause giữa segment trước và segment này
            pause_ms = (seg.start - prev_end) * 1000

            # Có pause đủ lớn → ngắt
            if pause_ms >= self.MIN_PAUSE_MS and buffer_text.strip():
                result.append(Segment(
                    start=round(buffer_start, 3),
                    end=round(prev_end, 3),
                    text=buffer_text.strip(),
                ))
                buffer_text = ""
                buffer_start = seg.start

            # Thêm text vào buffer
            buffer_text += seg.text

            # Kiểm tra ngắt tại dấu câu
            if buffer_text:
                last_char = buffer_text.rstrip()[-1] if buffer_text.rstrip() else ""

                # Dấu câu mạnh → luôn ngắt
                if last_char in self.BREAK_PUNCTUATION:
                    result.append(Segment(
                        start=round(buffer_start, 3),
                        end=round(seg.end, 3),
                        text=buffer_text.strip(),
                    ))
                    buffer_text = ""
                    buffer_start = seg.end

                # Dấu phẩy + đã dài → ngắt
                elif last_char in self.SOFT_BREAK and len(buffer_text) > 20:
                    result.append(Segment(
                        start=round(buffer_start, 3),
                        end=round(seg.end, 3),
                        text=buffer_text.strip(),
                    ))
                    buffer_text = ""
                    buffer_start = seg.end

                # Quá dài → ép ngắt
                elif len(buffer_text) > self.MAX_CHARS_PER_SUB:
                    # Tìm vị trí ngắt tốt nhất (space gần giữa)
                    split_pos = self._find_split_point(buffer_text)
                    first_part = buffer_text[:split_pos].strip()
                    remaining = buffer_text[split_pos:].strip()

                    # Ước lượng timing cho phần đầu
                    ratio = len(first_part) / len(buffer_text)
                    split_time = buffer_start + ratio * (seg.end - buffer_start)

                    result.append(Segment(
                        start=round(buffer_start, 3),
                        end=round(split_time, 3),
                        text=first_part,
                    ))
                    buffer_text = remaining
                    buffer_start = split_time

            prev_end = seg.end

        # Phần còn lại
        if buffer_text.strip():
            result.append(Segment(
                start=round(buffer_start, 3),
                end=round(prev_end, 3),
                text=buffer_text.strip(),
            ))

        return result

    def _find_split_point(self, text: str) -> int:
        """Tìm vị trí tốt nhất để ngắt text (ưu tiên dấu câu, space)."""
        mid = len(text) // 2

        # Ưu tiên ngắt tại dấu phẩy gần giữa
        for offset in range(min(15, mid)):
            for pos in [mid + offset, mid - offset]:
                if 0 < pos < len(text):
                    if text[pos] in (',', '，', ' ', '、'):
                        return pos + 1

        # Fallback: ngắt tại space gần giữa
        for offset in range(min(20, mid)):
            for pos in [mid + offset, mid - offset]:
                if 0 < pos < len(text) and text[pos] == ' ':
                    return pos + 1

        # Cuối cùng: ngắt giữa
        return mid
