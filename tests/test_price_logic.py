from unittest.mock import MagicMock
from price_checker import PriceChecker

def test_check_all_prices_pure_oop():
    mock_parser = MagicMock()
    mock_extractor = MagicMock()
    mock_db_manager = MagicMock() # Mock the manager
    
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db_manager.get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [(1, 102, "https://site.com", 500.0)]
    mock_extractor.extract_price.return_value = {"price": 309.0, "currency": "UAH"}

    # Inject the mock manager directly
    checker = PriceChecker(db_manager=mock_db_manager, parser=mock_parser, extractor=mock_extractor)
    checker.send_notification = MagicMock()
    
    checker.check_all_prices()
    
    checker.send_notification.assert_called_once()
