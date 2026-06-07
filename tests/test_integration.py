import os
import sqlite3
import pytest
from dotenv import load_dotenv

# Гарантуємо завантаження середовища перед імпортом модулів програми
load_dotenv()

from logger_config import get_logger
from price_checker import check_all_prices

logger = get_logger("tests.integration")

def test_price_change_trigger_notification():
    """Інтеграційний тест: підміна ціни в БД та автоматичний запуск чекера."""
    db_path = "tracker.db"
    
    # Крок 1: Валідація наявності БД
    assert os.path.exists(db_path), "Базу даних tracker.db не знайдено! Додайте товар через бота."
    
    logger.info("🧪 [TEST] Запуск інтеграційного тесту зміни ціни...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Крок 2: Перевірка наявності тестових даних
    cursor.execute("SELECT id, last_price FROM products")
    products = cursor.fetchall()
    if not products:
        conn.close()
        pytest.fail("База даних порожня. Додайте товар через бота перед запуском тесту.")
        
    logger.info(f"[TEST] Знайдено {len(products)} товарів. Мокаємо ціну на 1.0 UAH...")
    
    # Крок 3: Примусова підміна ціни для створення тригера
    cursor.execute("UPDATE products SET last_price = 1.0")
    conn.commit()
    conn.close()
    
    # Крок 4: Автоматичний запуск логіки чекера
    logger.info("[TEST] Автоматично викликаємо check_all_prices()...")
    try:
        check_all_prices()
        logger.info("🏁 [TEST] Інтеграційний тест завершено. Перевірте Telegram!")
    except Exception as e:
        pytest.fail(f"Чекер впав під час тестування: {e}")
