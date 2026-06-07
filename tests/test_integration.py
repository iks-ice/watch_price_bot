import os
import sqlite3
import pytest
from dotenv import load_dotenv

# Гарантуємо завантаження середовища перед ініціалізацією сервісів
load_dotenv()

from logger_config import get_logger
# Імпортуємо класи сервісів та головного чекера
from services import PlaywrightParser, GeminiPriceExtractor
from price_checker import PriceChecker

logger = get_logger("tests.integration")

def test_price_change_trigger_notification():
    """Інтеграційний тест: підміна ціни в БД та запуск об'єктного чекера цін."""
    db_path = "tracker.db"
    
    # Крок 1: Валідація наявності БД
    assert os.path.exists(db_path), "Базу даних tracker.db не знайдено! Додайте товар через бота."
    
    logger.info("🧪 [TEST] Запуск ООП-інтеграційного тесту зміни ціни...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Крок 2: Перевірка наявності тестових даних
        cursor.execute("SELECT id FROM products")
        products = cursor.fetchall()
        if not products:
            conn.close()
            pytest.fail("База даних порожня. Додайте товар через бота перед запуском тесту.")
            
        logger.info(f"[TEST] Знайдено {len(products)} товарів. Мокаємо ціну на 1.0 UAH...")
        
        # Крок 3: Примусова підміна ціни для створення тригера
        cursor.execute("UPDATE products SET last_price = 1.0")
        conn.commit()
        conn.close()
        
    except sqlite3.Error as e:
        pytest.fail(f"Помилка підготовки бази даних до тесту: {e}")
    
    # Крок 4: Збирання ООП-конструктора залежностей
    logger.info("[TEST] Ініціалізація сервісів та об'єкта PriceChecker...")
    parser_service = PlaywrightParser()
    llm_service = GeminiPriceExtractor()
    
    # Створюємо екземпляр класу чекера
    checker = PriceChecker(db_path=db_path, parser=parser_service, extractor=llm_service)
    
    # Крок 5: Автоматичний запуск логіки об'єктного чекера
    logger.info("[TEST] Автоматично викликаємо checker.check_all_prices()...")
    try:
        checker.check_all_prices()
        logger.info("🏁 [TEST] ООП-інтеграційний тест успішно завершено. Перевірте Telegram!")
    except Exception as e:
        pytest.fail(f"Об'єктний чекер впав під час тестування: {e}")
