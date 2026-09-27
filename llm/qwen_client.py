"""
LLM 客户端（阿里云百炼 OpenAI 兼容接口）
"""
import json
import re
from openai import OpenAI

from llm.base import LLMBase
from core.exceptions import LLMInferenceError
from utils.logger import get_logger

logger = get_logger(__name__)


class QwenClient(LLMBase):
    """Qwen 大模型客户端（阿里云百炼 OpenAI 兼容）"""

    def __init__(self, api_key: str, base_url: str, model_name: str = "qwen-plus"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def infer(self, prompt: str, temperature: float = 0.1) -> str:
        """调用 LLM 进行推理"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=0.9,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 推理失败: {e}")
            raise LLMInferenceError(f"LLM 推理失败: {e}")

    def infer_structured(self, prompt: str) -> dict:
        """结构化推理：自动解析 JSON 输出，失败则重试"""
        return self._retry_on_json_error(prompt)

    def _parse_json(self, text: str) -> dict:
        """从模型输出中提取并解析 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 用正则提取花括号内容
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise json.JSONDecodeError("无法解析 JSON", text, 0)

    def _retry_on_json_error(self, prompt: str, max_retries: int = 3) -> dict:
        """JSON 解析失败时自动重试"""
        for attempt in range(max_retries):
            try:
                output = self.infer(prompt)
                result = self._parse_json(output)
                return result
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败，第 {attempt + 1} 次重试")
                if attempt == max_retries - 1:
                    raise LLMInferenceError(f"LLM 输出无法解析为 JSON，已重试 {max_retries} 次")
        raise LLMInferenceError("未知错误")
