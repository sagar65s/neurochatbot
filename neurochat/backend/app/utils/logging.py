"""
Simple structured logging helper. Ensures we never accidentally log
secrets (API keys, tokens, private keys) even if a caller passes them in.
"""
import logging
import sys

SENSITIVE_KEYS = {
    "api_key",
    "private_key",
    "authorization",
    "token",
    "id_token",
    "firebase_private_key",
}


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def safe_extra(data: dict) -> dict:
    """Redact sensitive fields before logging a dict."""
    return {
        k: ("***REDACTED***" if k.lower() in SENSITIVE_KEYS else v)
        for k, v in data.items()
    }
