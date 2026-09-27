"""
全局配置管理
优先级：环境变量 > .env 文件 > 代码默认值
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class Settings:
    """全局配置类，集中管理所有参数"""

    # 讯飞 ASR 配置
    XUNFEI_APPID: str = ""
    XUNFEI_API_KEY: str = ""
    XUNFEI_API_SECRET: str = ""
    XUNFEI_WS_URL: str = "wss://iat.cn-huabei-1.xf-yun.com/v1"

    # LLM 配置（阿里云百炼 OpenAI 兼容）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://ws-h7cqylclyq1uator.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL_NAME: str = "qwen3.7-flash-2026-07-15"

    # 音频配置
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_BIT_DEPTH: int = 16
    AUDIO_CHUNK_SECONDS: int = 55

    # 输出配置
    OUTPUT_DIR: str = "data/output"

    @classmethod
    def load_from_env(cls) -> "Settings":
        """从 .env 文件和环境变量加载配置（环境变量优先级更高）"""
        load_dotenv()
        return cls(
            XUNFEI_APPID=os.getenv("XUNFEI_APPID", ""),
            XUNFEI_API_KEY=os.getenv("XUNFEI_API_KEY", ""),
            XUNFEI_API_SECRET=os.getenv("XUNFEI_API_SECRET", ""),
            XUNFEI_WS_URL=os.getenv("XUNFEI_WS_URL", "wss://iat.cn-huabei-1.xf-yun.com/v1"),
            LLM_API_KEY=os.getenv("LLM_API_KEY", ""),
            LLM_BASE_URL=os.getenv("LLM_BASE_URL", "https://ws-h7cqylclyq1uator.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"),
            LLM_MODEL_NAME=os.getenv("LLM_MODEL_NAME", "qwen-plus"),
            AUDIO_SAMPLE_RATE=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
            AUDIO_CHANNELS=int(os.getenv("AUDIO_CHANNELS", "1")),
            AUDIO_BIT_DEPTH=int(os.getenv("AUDIO_BIT_DEPTH", "16")),
            AUDIO_CHUNK_SECONDS=int(os.getenv("AUDIO_CHUNK_SECONDS", "55")),
            OUTPUT_DIR=os.getenv("OUTPUT_DIR", "data/output"),
        )
