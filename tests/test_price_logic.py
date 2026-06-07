import pytest
from unittest.mock import MagicMock, patch
from price_checker import PriceChecker

def test_check_all_prices_pure_oop():
    """Тестування логіки чекера через чисте впровадження залежностей (без @patch для функцій)."""
    
    # 1. Створюємо чисті ізольовані мок-сервіси
    mock_parser = MagicMock()
    mock_extractor = MagicMock()
    
    # Імітуємо, що ШІ завжди повертає ціну 309
    mock_extractor.extract_price.return_value = {"price": 309.0, "currency": "UAH"}
    
    # 2. Мокаємо тільки підключення до бази даних, щоб не створювати реальний файл
    with patch("sqlite3.connect") as mock_sql_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sql_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Набір товарів: один товар змінив ціну з 500 на 309
        mock_cursor.fetchall.return_value = [
            (1, 102, "https://site.com", 500.0)
        ]
        
        # Ініціалізуємо об'єкт чекера, явно передаючи підроблені сервіси
        checker = PriceChecker(db_path="fake.db", parser=mock_parser, extractor=mock_extractor)
        
        # Перевизначаємо метод відправки сповіщень, щоб не йти в інтернет
        checker.send_notification = MagicMock()
        
        # Запускаємо цільову логіку
        checker.check_all_prices()
        
        # 3. Перевіряємо бізнес-правила
        # Чи зафіксувала система зміну ціни і чи викликала сповіщення?
        checker.send_notification.assert_called_once_with(
            102, "https://site.com", 500.0, 309.0, "UAH"
        )
