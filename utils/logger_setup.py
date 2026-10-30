"""
logger_setup.py
----------------
Configures application-wide logging. Logs go to both a rotating file
(logs/fno_analyzer.log) and the console, so issues can be diagnosed
after the fact without asking the user to reproduce them.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config.constants import LOG_DIR, LOG_FILE


def setup_logger(name: str = "fno_analyzer") -> logging.Logger:
    """
    Create and configure a logger instance.

    Safe to call multiple times (e.g. from different modules) -- handlers
    are only attached once per logger name.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured (e.g. imported from another module) - reuse it.
        return logger

    logger.setLevel(logging.DEBUG)

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, LOG_FILE)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
