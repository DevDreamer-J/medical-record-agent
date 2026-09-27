"""
长音频切割模块
使用 ffmpeg 直接实现固定时长切割（带重叠），避免 pydub 在 Python 3.13+ 的 audioop 兼容问题
"""
import os
import re
import subprocess
import imageio_ffmpeg

from core.exceptions import AudioProcessError
from utils.logger import get_logger

logger = get_logger(__name__)


class AudioSplitter:
    """长音频切割模块"""

    def __init__(self, chunk_seconds: int = 55, overlap_seconds: float = 2.0):
        self.chunk_seconds = chunk_seconds
        self.overlap_seconds = overlap_seconds
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def split(self, audio_path: str, output_dir: str) -> list:
        """
        切割音频，返回切割后的文件路径列表
        使用固定时长切割 + 段间重叠
        """
        os.makedirs(output_dir, exist_ok=True)
        duration = self._get_duration(audio_path)
        if duration <= 0:
            raise AudioProcessError(f"无法获取音频时长: {audio_path}")

        chunk_ms = self.chunk_seconds * 1000
        overlap_ms = int(self.overlap_seconds * 1000)
        total_ms = int(duration * 1000)

        output_paths = []
        idx = 0
        pos = 0

        while pos < total_ms:
            # 每段起点往回退 overlap（非首段），避免语句被切断
            start_ms = max(0, pos - overlap_ms) if idx > 0 else 0
            end_ms = min(pos + chunk_ms, total_ms)
            seg_duration = (end_ms - start_ms) / 1000.0

            out_path = os.path.join(output_dir, f"chunk_{idx:04d}.wav")
            self._extract_segment(audio_path, out_path, start_ms / 1000.0, seg_duration)
            output_paths.append(out_path)

            pos += chunk_ms
            idx += 1

        logger.info(f"音频切割完成，共 {len(output_paths)} 段（时长 {duration:.1f}s）")
        return output_paths

    def _extract_segment(self, input_path: str, output_path: str, start_sec: float, duration_sec: float):
        """用 ffmpeg 提取音频片段"""
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-ss", f"{start_sec:.3f}",
            "-i", input_path,
            "-t", f"{duration_sec:.3f}",
            "-ar", "16000",
            "-ac", "1",
            "-sample_fmt", "s16",
            "-acodec", "pcm_s16le",
            output_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise AudioProcessError(f"音频切割失败: {result.stderr[:300]}")
        except subprocess.TimeoutExpired:
            raise AudioProcessError("音频切割超时")

    def _get_duration(self, audio_path: str) -> float:
        """获取音频时长（秒）"""
        cmd = [self.ffmpeg_exe, "-i", audio_path, "-hide_banner"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            for line in result.stderr.splitlines():
                if "Duration:" in line:
                    time_str = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = time_str.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0

    def merge_transcripts(self, transcripts: list) -> str:
        """合并多段识别结果，简单拼接"""
        return "".join(transcripts)
