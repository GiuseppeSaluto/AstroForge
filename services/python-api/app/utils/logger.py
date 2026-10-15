import logging
import os
from logging.handlers import RotatingFileHandler
from app.core.config import LOG_DIRECTORY

os.makedirs(LOG_DIRECTORY, exist_ok=True)

logger = logging.getLogger("astroforge")
logger.setLevel(logging.INFO)

log_path = os.path.join(LOG_DIRECTORY, "python_api.log")

# Bounded: 5 MB x 3 backups. /logs only reads the current file.
file_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
