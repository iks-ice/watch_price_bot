import sys
import os
from dotenv import load_dotenv

# Load execution environment state flags as the highest order operation
load_dotenv()

from logger_config import get_logger
from database import DatabaseManager

logger = get_logger("main")

def main():
    if len(sys.argv) < 2:
        logger.error("Execution terminated: Missing required runtime mode argument specification.")
        sys.exit(1)

    mode = sys.argv[1].lower()
    
    # Initialize the global singular infrastructure manager container instance
    db_manager = DatabaseManager()

    if mode == "bot":
         # 1. Import all required domain core service nodes for dependency assembly orchestration
        from services import PlaywrightParser, GeminiPriceExtractor
        from price_checker import PriceChecker
        from bot import TelegramPriceBot
        
        # 2. Construct instances to support the newly exposed on-demand /check runtime pipelines
        parser_service = PlaywrightParser()
        llm_service = GeminiPriceExtractor()
        price_checker_service = PriceChecker(db_manager=db_manager, parser=parser_service, extractor=llm_service)
        
        # 3. Inject the prepared price checker instance right into the main application daemon container node
        bot_service = TelegramPriceBot(
            token=os.getenv("TELEGRAM_TOKEN"), 
            db_manager=db_manager, 
            price_checker=price_checker_service
        )
        
        try:
            bot_service.start_polling()
        except Exception:
            logger.exception("Fatal runtime unhandled exception terminated the active Bot polling loop")
            sys.exit(1)

    elif mode == "check":
        # Lazy structural dependency binding for active background processing scope execution
        from services import PlaywrightParser, GeminiPriceExtractor
        from price_checker import PriceChecker

        parser_service = PlaywrightParser()
        llm_service = GeminiPriceExtractor()
        
        checker = PriceChecker(db_manager=db_manager, parser=parser_service, extractor=llm_service)
        try:
            checker.check_all_prices()
        except Exception:
            logger.exception("Fatal background execution event terminated the pricing evaluation tracker execution")
            sys.exit(1)

    else:
        logger.error(f"Execution rejected: Unknown initialization runtime flag parameter instruction '{mode}' received.")
        sys.exit(1)

if __name__ == "__main__":
    main()
