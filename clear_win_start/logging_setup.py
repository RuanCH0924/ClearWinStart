"""
日志系统：彩色控制台输出 + 滚动文件日志。
"""

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from clear_win_start.paths import get_default_log_path

__all__ = [
    "LOG_FORMAT",
    "LOG_DATE_FORMAT",
    "LOG_FORMAT_DETAILED",
    "ColoredFormatter",
    "setup_logging",
    "mask_sensitive_info",
]


LOG_FORMAT = "%(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT_DETAILED = "[%(filename)s:%(lineno)d] - %(message)s"

LEVEL_COLORS = {
    "DEBUG": "\033[90m",      # 灰
    "INFO": "\033[0m",        # 默认
    "WARNING": "\033[93m",    # 黄
    "ERROR": "\033[91m",      # 红
    "CRITICAL": "\033[91m",   # 红
    "SUCCESS": "\033[92m",    # 绿
}

LEVEL_PREFIXES = {
    "ERROR": "❌ ",
    "WARNING": "⚠️  ",
    "CRITICAL": "🚨 ",
}

RESET = "\033[0m"

SENSITIVE_KEYWORDS = (
    "password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
    "auth", "credential", "private_key", "access_token", "refresh_token",
)


class ColoredFormatter(logging.Formatter):
    """为控制台输出着色的 Formatter。"""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.levelname in LEVEL_PREFIXES:
            message = LEVEL_PREFIXES[record.levelname] + message

        color = LEVEL_COLORS.get(record.levelname, "")
        if color:
            return f"{color}{message}{RESET}"
        return message


def mask_sensitive_info(message: str) -> str:
    """屏蔽日志中包含敏感字段的值。"""
    result = message
    for keyword in SENSITIVE_KEYWORDS:
        pattern = rf"({keyword}['\"]?\s*[:=]\s*['\"]?)([^'\"\s,}}]+)"
        result = re.sub(pattern, r"\1*****", result, flags=re.IGNORECASE)
    return result


def setup_logging(
    verbose: bool = False,
    log_file: Optional[str] = None,
    log_level_console: Optional[str] = None,
    log_level_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """初始化 logging：彩色控制台 + 可选滚动文件日志。"""
    console_level = getattr(logging, log_level_console or ("DEBUG" if verbose else "INFO"))
    file_level = getattr(logging, log_level_file or ("DEBUG" if verbose else "INFO"))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清空旧 handler（CLI/GUI 重复调用安全）
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColoredFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    root_logger.addHandler(console_handler)

    log_path = log_file or get_default_log_path()
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT_DETAILED, datefmt=LOG_DATE_FORMAT))
    root_logger.addHandler(file_handler)

    logging.getLogger("clear_win_start").setLevel(
        logging.DEBUG if verbose else logging.INFO
    )
