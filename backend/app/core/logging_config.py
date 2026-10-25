import re
import logging
import sys
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that redacts credentials, authorization tokens, and encryption keys
    from log records before output.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact_string(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (self.redact_string(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.redact_string(a) if isinstance(a, str) else a for a in record.args)
        return True

    @staticmethod
    def redact_string(value: str) -> str:
        if not value or not isinstance(value, str):
            return value
        
        # Redact key-value style credentials (JSON, query params, headers)
        redacted = re.sub(
            r'(["\']?(?:password|passwd|secret|token|api_key|access_token|authorization|auth_token|csrf_token|jwt|encryption_key)["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])',
            r'\1[REDACTED]\3',
            value,
            flags=re.IGNORECASE
        )
        
        # Redact Bearer auth tokens
        redacted = re.sub(
            r'(Bearer\s+)[A-Za-z0-9\-_.]+',
            r'\1[REDACTED]',
            redacted,
            flags=re.IGNORECASE
        )
        
        return redacted


def setup_logging(level: str = "INFO", log_to_file: Optional[str] = None):
    """
    Configures secure application logging with standardized ISO timestamps,
    appropriate log level, and redaction of sensitive credentials.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing stream handlers to prevent duplicate lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)
    
    if log_to_file:
        file_handler = logging.FileHandler(log_to_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
