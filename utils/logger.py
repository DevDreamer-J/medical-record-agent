"""日志工具"""
import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(name: str = "medical_record_agent") -> logging.Logger:
    """
    获取统一配置的日志器
    控制台输出 + 文件输出（带轮转）
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 控制台
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # 文件（轮转，单文件最大 5MB，保留 3 个备份）
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        "logs/agent.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
