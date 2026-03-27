"""Logging configuration — supports JSON (Logstash) and plain text formats"""
import logging
import logging.handlers
import os
from pathlib import Path
from app.core.config import settings

Path("logs").mkdir(exist_ok=True)

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

# Choose formatter: JSON when LOGSTASH_HOST is configured, plain text otherwise
_use_json = bool(os.getenv("LOGSTASH_HOST"))

if _use_json:
    try:
        from pythonjsonlogger import jsonlogger

        _stream_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    except ImportError:
        _stream_formatter = logging.Formatter(_LOG_FORMAT)
        _use_json = False
else:
    _stream_formatter = logging.Formatter(_LOG_FORMAT)

# Stream handler (stdout / Logstash via TCP)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_stream_formatter)

# Rotating file handler (always plain text for human-readable local logs)
_file_handler = logging.handlers.RotatingFileHandler(
    settings.LOG_FILE,
    maxBytes=10_485_760,  # 10 MB
    backupCount=10,
)
_file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))

root_logger = logging.getLogger()
root_logger.setLevel(_log_level)
root_logger.addHandler(_stream_handler)
root_logger.addHandler(_file_handler)

# Reduce noise from third-party libraries
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
