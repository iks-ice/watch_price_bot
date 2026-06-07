import sys
from dotenv import load_dotenv

load_dotenv()

from logger_config import get_logger
logger = get_logger("main")

def main():
    if len(sys.argv) < 2:
        logger.error("Запуск відхилено: Не вказано режим роботи програми.")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "bot":
        from bot import init_db, bot as telegram_bot
        init_db()
        logger.info("🚀 Запуск Telegram-бота...")
        telegram_bot.infinity_polling()

    elif mode == "check":
        # ЗБИРАЄМО ЗАЛЕЖНОСТІ (Dependency Injection)
        from services import PlaywrightParser, GeminiPriceExtractor
        from price_checker import PriceChecker

        parser_service = PlaywrightParser()
        llm_service = GeminiPriceExtractor()
        
        # Передаємо створені сервіси всередину чекера
        checker = PriceChecker(db_path="tracker.db", parser=parser_service, extractor=llm_service)
        
        try:
            checker.check_all_prices()
        except Exception:
            logger.exception("Критичний збій об'єктного чекера")
            sys.exit(1)
    else:
        logger.error(f"Невідомий режим '{mode}'")
        sys.exit(1)

if __name__ == "__main__":
    main()
