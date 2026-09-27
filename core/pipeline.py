"""
主流程编排器
串联：音频预处理 → ASR 识别 → LLM 结构化 → Word 生成
支持中间产物持久化（transcript.txt, structured.json）
"""
import json
import os
import tempfile

from config.settings import Settings
from audio.preprocessor import AudioPreprocessor
from audio.splitter import AudioSplitter
from asr.xunfei_asr import XunfeiASR
from llm.prompt_builder import PromptBuilder
from llm.qwen_client import QwenClient
from document.validator import RecordValidator
from document.word_generator import WordGenerator
from utils.logger import get_logger

logger = get_logger(__name__)


class MedicalRecordPipeline:
    """病历生成主流程编排器"""

    def __init__(self, config: Settings):
        self.config = config
        self.preprocessor = AudioPreprocessor(
            sample_rate=config.AUDIO_SAMPLE_RATE,
            channels=config.AUDIO_CHANNELS,
            bit_depth=config.AUDIO_BIT_DEPTH,
        )
        self.splitter = AudioSplitter(chunk_seconds=config.AUDIO_CHUNK_SECONDS)
        self.asr = XunfeiASR(
            appid=config.XUNFEI_APPID,
            api_key=config.XUNFEI_API_KEY,
            api_secret=config.XUNFEI_API_SECRET,
            ws_url=config.XUNFEI_WS_URL,
        )
        self.prompt_builder = PromptBuilder()
        self.llm = QwenClient(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            model_name=config.LLM_MODEL_NAME,
        )
        self.validator = RecordValidator()
        self.word_generator = WordGenerator(output_dir=config.OUTPUT_DIR)

    def run(self, audio_path: str, output_name: str = None) -> str:
        """
        执行完整病历生成流程
        :return: 生成的 Word 文档路径
        """
        # 创建本次输出目录（按音频文件名）
        audio_stem = os.path.splitext(os.path.basename(audio_path))[0]
        run_dir = os.path.join(self.config.OUTPUT_DIR, audio_stem)
        os.makedirs(run_dir, exist_ok=True)

        # 步骤1：音频预处理
        logger.info("===== 步骤1：音频预处理 =====")
        converted_path = os.path.join(run_dir, "converted.wav")
        self._process_audio(audio_path, converted_path)

        # 步骤2：语音识别（长音频先切割）
        logger.info("===== 步骤2：语音识别 =====")
        transcript = self._recognize(converted_path, run_dir)
        # 持久化转写文本
        transcript_path = os.path.join(run_dir, "transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        logger.info(f"转写文本已保存: {transcript_path}")

        # 步骤3：LLM 结构化
        logger.info("===== 步骤3：LLM 结构化 =====")
        record = self._structure(transcript)
        # 持久化结构化结果
        structured_path = os.path.join(run_dir, "structured.json")
        with open(structured_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        logger.info(f"结构化结果已保存: {structured_path}")

        # 步骤4：校验 + 生成 Word
        logger.info("===== 步骤4：生成 Word 文档 =====")
        warnings = self.validator.validate(record)
        for w in warnings:
            logger.warning(f"校验警告: {w}")

        output_path = self._generate_word(record, run_dir, output_name)
        logger.info(f"===== 流程完成，病历路径: {output_path} =====")
        return output_path

    def _process_audio(self, input_path: str, output_path: str) -> str:
        """步骤1：音频预处理（格式转换 + 音量标准化）"""
        self.preprocessor.convert(input_path, output_path)
        self.preprocessor.normalize_volume(output_path)
        return output_path

    def _recognize(self, audio_path: str, run_dir: str) -> str:
        """步骤2：语音识别，长音频先切割再合并"""
        duration = self.preprocessor.get_duration(audio_path)
        logger.info(f"音频时长: {duration:.1f} 秒")

        if duration > self.config.AUDIO_CHUNK_SECONDS:
            # 长音频切割
            chunk_dir = os.path.join(run_dir, "chunks")
            chunk_paths = self.splitter.split(audio_path, chunk_dir)
            transcripts = self.asr.recognize_batch(chunk_paths)
            return self.splitter.merge_transcripts(transcripts)
        else:
            return self.asr.recognize(audio_path)

    def _structure(self, transcript: str) -> dict:
        """步骤3：LLM 结构化提取病历字段"""
        prompt = self.prompt_builder.build(transcript)
        return self.llm.infer_structured(prompt)

    def _generate_word(self, record: dict, run_dir: str, output_name: str = None) -> str:
        """步骤4：生成 Word 文档"""
        # Word 文件直接输出到 run_dir
        self.word_generator.output_dir = run_dir
        return self.word_generator.generate(record, output_name)
