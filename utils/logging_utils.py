import logging
import os
import sys
from typing import Optional

def get_log_level(level: str) -> int:
    return getattr(logging, level, logging.INFO)

def setup_logging(
    log_level: int = logging.INFO,
    log_dir: Optional[str] = None,
    logger_name: Optional[str] = None,
) -> logging.Logger:
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
    os.makedirs(log_dir, exist_ok=True)
    if logger_name is None:
        logger_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    log_path = os.path.join(log_dir, f"{logger_name}.log")

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.handlers.clear()
    # File handler
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=datefmt))
    logger.addHandler(file_handler)
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=datefmt))
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger
