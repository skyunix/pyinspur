import os
import sys
from datetime import datetime

from loguru import logger as loguru_logger


def setup_logging(log_level: str = "INFO") -> None:
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(
        log_dir, f"pyinspur_{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    )

    loguru_logger.remove()

    loguru_logger.add(
        log_filename,
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        encoding="utf-8",
        rotation="500 MB",
        retention="10 days",
    )

    console_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}"
    if log_level.upper() == "DEBUG":
        console_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        )

    loguru_logger.add(
        sys.stdout,
        level=log_level.upper(),
        format=console_format,
        colorize=True,
    )


def get_logger(name: str):
    return loguru_logger
