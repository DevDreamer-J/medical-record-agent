"""
语音病历生成 Agent - 启动入口
用法：
    python main.py --audio data/input/recording.mp3
    python main.py --audio data/input/ --batch   # 批量处理
"""
import argparse
import os
import sys

from config.settings import Settings
from core.pipeline import MedicalRecordPipeline
from utils.logger import get_logger

logger = get_logger(__name__)

# 支持的音频后缀
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".amr", ".opus"}


def main():
    parser = argparse.ArgumentParser(description="语音病历生成 Agent")
    parser.add_argument("--audio", type=str, required=True, help="音频文件路径或目录")
    parser.add_argument("--batch", action="store_true", help="批量处理模式（处理目录下所有音频）")
    args = parser.parse_args()

    # 加载配置
    config = Settings.load_from_env()

    # 校验关键配置
    if not config.XUNFEI_APPID or config.XUNFEI_APPID == "xxxxx":
        logger.error("请在 .env 文件中配置讯飞 ASR 凭证")
        sys.exit(1)
    if not config.LLM_API_KEY:
        logger.error("请在 .env 文件中配置 LLM API Key")
        sys.exit(1)

    # 创建流程实例
    pipeline = MedicalRecordPipeline(config)

    if args.batch:
        # 批量处理目录下所有音频
        if not os.path.isdir(args.audio):
            logger.error(f"批量模式需要提供目录路径: {args.audio}")
            sys.exit(1)
        audio_files = [
            os.path.join(args.audio, f)
            for f in os.listdir(args.audio)
            if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS
        ]
        if not audio_files:
            logger.error(f"目录下未找到音频文件: {args.audio}")
            sys.exit(1)
        logger.info(f"批量处理 {len(audio_files)} 个音频文件")
        for audio_file in audio_files:
            try:
                output = pipeline.run(audio_file)
                logger.info(f"处理完成: {audio_file} -> {output}")
            except Exception as e:
                logger.error(f"处理失败 {audio_file}: {e}")
    else:
        # 单文件处理
        if not os.path.exists(args.audio):
            logger.error(f"音频文件不存在: {args.audio}")
            sys.exit(1)
        output_path = pipeline.run(args.audio)
        print(f"\n✅ 病历已生成：{output_path}")


if __name__ == "__main__":
    main()
