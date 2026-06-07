import sqlite3
import pytest
from unittest.mock import patch, MagicMock

# Використовуємо create=True, щоб mock не падав через особливості імпорту функцій у вашому price_checker.py
@patch("price_checker.get_page_text")
@patch("price_checker.extract_price_with_llm")
@patch("price_checker.send_notification")
@patch("sqlite3.connect")
def test_check_all_prices_logic(mock_sql_connect, mock_send_notification, mock_extract_llm, mock_get_page):
    """Юніт-тест бізнес-логіки порівняння цін без доступу до мережі та БД."""
    
    # 1. Імітуємо набір товарів з різними станами:
    # Товар 1: Новий (last_price = 0) -> має зробити UPDATE
    # Товар 2: Ціна змінилася (500 != 309) -> має зробити UPDATE та відправити сповіщення
    # Товар 3: Ціна стабільна (309 == 309) -> нічого не робить
    mock_products = [
        (1, 101, "https://site.com", 0.0),   
        (2, 102, "https://site.com", 500.0), 
        (3, 103, "https://site.com", 309.0)  
    ]
    
    # Налаштування моку для SQLite коннектора та курсора
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_sql_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = mock_products
    
    # 2. Перехоплюємо виклики зовнішніх API
    mock_get_page.return_value = "<html>Mock HTML</html>"
    mock_extract_llm.return_value = {"price": 309.0, "currency": "UAH"}
    
    # Імпортуємо функцію чекера всередині тесту, щоб патчі вже діяли
    from price_checker import check_all_prices
    
    # Запускаємо цільову логіку
    check_all_prices()
    
    # 3. Асерти (Верифікація результатів)
    # Перевіряємо, чи була виконана команда UPDATE (мінімум 2 рази для нових/змінених товарів)
    assert mock_cursor.execute.call_count >= 2
    
    # Перевіряємо, чи було надіслано сповіщення РІВНО один раз і саме для товару №2
    mock_send_notification.assert_called_once_with(
        102, "https://site.com", 500.0, 309.0, "UAH"
    )
