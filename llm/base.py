"""LLM 抽象基类"""
from abc import ABC, abstractmethod


class LLMBase(ABC):
    """LLM 服务抽象基类"""

    @abstractmethod
    def infer(self, prompt: str, temperature: float = 0.1) -> str:
        """调用 LLM 进行推理，返回文本"""
        pass

    @abstractmethod
    def infer_structured(self, prompt: str) -> dict:
        """结构化推理，返回解析后的字典"""
        pass
