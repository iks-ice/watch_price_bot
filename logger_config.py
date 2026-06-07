import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Tuple

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Оновлений формат: додано мітку [User: %(user_id)s]
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] [User: %(user_id)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

file_handler = RotatingFileHandler(
    filename=os.path.join(LOGS_DIR, "tracker.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8"
)
stream_handler = logging.StreamHandler(sys.stdout)

formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

class UserContextAdapter(logging.LoggerAdapter):
    """Адаптер, який автоматично додає або форматує user_id в логах."""
    def process(self, msg: Any, kwargs: Any) -> Tuple[Any, Dict[str, Any]]:
        # Якщо в extra не передали user_id, ставимо прочерк
        if "user_id" not in self.extra:
            self.extra["user_id"] = "-"
        
        # Підтримуємо можливість перевизначити user_id безпосередньо у виклику logger.info(..., extra={"user_id": X})
        if "extra" in kwargs:
            kwargs["extra"].update(self.extra)
        else:
            kwargs["extra"] = self.extra
            
        return msg, kwargs

def get_logger(module_name: str) -> UserContextAdapter:
    """Повертає адаптований логгер."""
    logger = logging.getLogger(f"app.{module_name}")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    # Повертаємо адаптер з порожнім дефолтним extra контекстом
    return UserContextAdapter(logger, {})
