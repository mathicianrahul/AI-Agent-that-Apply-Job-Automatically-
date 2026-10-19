import logging
import re
import sys
from typing import Any

from jobpilot.config import settings

# Sensitive patterns to redact
SENSITIVE_PATTERNS = [
    re.compile(r'(?i)(token|api[_-]?key|password|secret|bearer)\s*[:=]\s*([\'"]?)([^\s\'",]+)(\2)'),
    re.compile(r'(?i)(hf_[a-zA-Z0-9]{20,})'),
]


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern in SENSITIVE_PATTERNS:
            msg = pattern.sub(r'\1: [REDACTED]', msg)
        return msg


def setup_logger(name: str = "jobpilot") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = RedactingFormatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
