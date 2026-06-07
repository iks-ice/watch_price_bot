import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    # Створюємо папку для логів у колі проєкту, якщо її немає
    os.makedirs("logs", exist_ok=True)

    # Загальне налаштування базового логгера
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            # Лог-файл з авто-ротацією при досягненні 5 МБ (максимум 3 архівні файли)
            RotatingFileHandler("logs/tracker.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
            # Одночасний вивід у консоль
            logging.StreamHandler()
        ]
    )
    
    # Повертаємо налаштований головний логгер
    return logging.getLogger("price_tracker")

# Створюємо екземпляр логгера для імпорту в інші файли
logger = setup_logger()
