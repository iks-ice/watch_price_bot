import os
import sqlite3
import pytest
from dotenv import load_dotenv

# Load local environment configuration profile keys
load_dotenv()

from logger_config import get_logger
from database import DatabaseManager
from services import PlaywrightParser, GeminiPriceExtractor
from price_checker import PriceChecker

logger = get_logger("tests.integration")

def test_price_change_trigger_notification():
    """Integration test: forces database state manipulation to trigger the entire pipeline workflow."""
    db_path = os.getenv("DATABASE_PATH", "tracker.db")
    
    # Step 1: Ensure database profile metadata container storage file exists safely
    assert os.path.exists(db_path), "Database target tracker.db was not located. Add an item via the bot engine first."
    
    logger.info("🧪 [TEST] Initializing OOP-driven integration price alteration test pipeline...")
    
    # Step 2: Initialize database infrastructure container instance manager service
    db_manager = DatabaseManager()
    
    try:
        # Step 3: Manipulate current last_price record states safely using the connection pool manager
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM products")
            products = cursor.fetchall()
            
            if not products:
                pytest.fail("Target storage schema is currently empty. Populate items manually via the bot first.")
                
            logger.info(f"[TEST] Located {len(products)} tracking records. Mocking baseline data to 1.0 UAH...")
            
            # Reset values to trigger inequality statement block evaluations later (new_price != last_price)
            cursor.execute("UPDATE products SET last_price = 1.0")
            conn.commit()
            
    except sqlite3.Error as e:
        pytest.fail(f"Persistent storage preparation routine encountered a critical error exception: {e}")
    
    # Step 4: Assemble active dependency injection tracking architecture layer structures
    logger.info("[TEST] Assembling OOP component architecture nodes...")
    parser_service = PlaywrightParser()
    llm_service = GeminiPriceExtractor()
    
    # Inject the actual database manager instance into the business director controller
    checker = PriceChecker(db_manager=db_manager, parser=parser_service, extractor=llm_service)
    
    # Step 5: Execute un-mocked edge pricing lookup update tasks
    logger.info("[TEST] Programmatically invoking live pricing evaluator: checker.check_all_prices()...")
    try:
        checker.check_all_prices()
        logger.info("🏁 [TEST] OOP Integration integration pipeline routine evaluation successful. Verify chat!")
    except Exception as e:
        pytest.fail(f"Active pricing processing engine context crashed during live test execution: {e}")
