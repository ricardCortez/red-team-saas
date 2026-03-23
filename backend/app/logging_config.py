"""Logging configuration"""
import logging
import logging.handlers
from pathlib import Path
from app.core.config import settings

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

file_handler = logging.handlers.RotatingFileHandler(
    settings.LOG_FILE,
    maxBytes=10485760,
    backupCount=10,
)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)
