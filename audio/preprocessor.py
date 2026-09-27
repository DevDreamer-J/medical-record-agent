"""
音频预处理模块
负责将任意格式音频转换为 ASR 要求的标准格式（16kHz 单声道 16bit PCM WAV）
使用 imageio-ffmpeg 内置的 ffmpeg 二进制，无需系统安装 ffmpeg
"""
import os
import subprocess
import imageio_ffmpeg
from core.exceptions import AudioProcessError
from utils.logger import get_logger

logger = get_logger(__name__)

# 支持的音频后缀
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".amr", ".opus"}


class AudioPreprocessor:
    """音频预处理模块"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, bit_depth: int = 16):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bit_depth = bit_depth
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def convert(self, input_path: str, output_path: str) -> str:
        """
        格式转换：任意格式 → 16kHz 单声道 16bit WAV (PCM)
        """
        ext = os.path.splitext(input_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise AudioProcessError(f"不支持的音频格式: {ext}，支持: {SUPPORTED_EXTENSIONS}")

        if not os.path.exists(input_path):
            raise AudioProcessError(f"音频文件不存在: {input_path}")

        # 使用 ffmpeg 转换：-ar 采样率 -ac 声道数 -sample_fmt 位深
        # s16le = 16-bit little-endian PCM
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-i", input_path,
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-sample_fmt", "s16",
            "-acodec", "pcm_s16le",
            output_path,
        ]
        logger.info(f"转换音频: {input_path} -> {output_path}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"ffmpeg 转换失败: {result.stderr}")
                raise AudioProcessError(f"音频转换失败: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            raise AudioProcessError("音频转换超时")
        except FileNotFoundError:
            raise AudioProcessError("ffmpeg 未找到，请检查 imageio-ffmpeg 安装")

        if not os.path.exists(output_path):
            raise AudioProcessError("转换后文件未生成")

        logger.info("音频转换完成")
        return output_path

    def normalize_volume(self, audio_path: str) -> str:
        """音量标准化（loudnorm 滤镜），原地覆盖，保持 16kHz 单声道 16bit"""
        tmp_path = audio_path + ".tmp.wav"
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-i", audio_path,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-sample_fmt", "s16",
            "-acodec", "pcm_s16le",
            tmp_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(tmp_path):
                os.replace(tmp_path, audio_path)
                logger.info("音量标准化完成")
            else:
                logger.warning(f"音量标准化失败，跳过: {result.stderr[:200]}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            logger.warning(f"音量标准化异常，跳过: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return audio_path

    def get_duration(self, audio_path: str) -> float:
        """获取音频时长（秒）"""
        cmd = [
            self.ffmpeg_exe,
            "-i", audio_path,
            "-hide_banner",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # 从 stderr 中解析 Duration
            for line in result.stderr.splitlines():
                if "Duration:" in line:
                    time_str = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = time_str.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0
