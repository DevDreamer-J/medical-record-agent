"""ASR 服务抽象基类"""
from abc import ABC, abstractmethod


class ASRBase(ABC):
    """ASR 服务抽象基类，便于后续切换其他 ASR 服务商"""

    @abstractmethod
    def recognize(self, audio_path: str) -> str:
        """识别单个音频文件，返回识别文本"""
        pass

    def recognize_batch(self, audio_paths: list) -> list:
        """批量识别音频文件，默认串行实现"""
        return [self.recognize(p) for p in audio_paths]
