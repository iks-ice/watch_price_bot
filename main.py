import sys
from dotenv import load_dotenv

# 1. Найперший крок — завантаження середовища
load_dotenv()

# 2. Імпорт налаштованого логгера
from logger_config import get_logger
logger = get_logger("main")

def main():
    # Валідація наявності аргументів CLI
    if len(sys.argv) < 2:
        logger.error(
            "Запуск відхилено: Не вказано режим роботи програми. "
            "Використання: 'python main.py bot' або 'python main.py check'"
        )
        sys.exit(1)

    # Приведення аргументу до нижнього регістру (захист від sys.argv.lower() помилки)
    mode = sys.argv[1].lower()

    if mode == "bot":
        # Лінивий імпорт для ізоляції телеграм-клієнта
        from bot import init_db, bot as telegram_bot
        
        init_db()
        logger.info("🚀 Запуск Telegram-бота у режимі Infinity Polling...")
        try:
            telegram_bot.infinity_polling()
        except Exception:
            logger.exception("Критичний збій у роботі циклу Telegram-бота")
            sys.exit(1)

    elif mode == "check":
        # Лінивий імпорт для ізоляції чекера цін
        from bot import init_db
        from price_checker import check_all_prices
        
        init_db()
        logger.info("🔄 Запуск перевірки цін за допомогою Gemini LLM...")
        try:
            check_all_prices()
            logger.info("✅ Перевірка всіх цін успішно завершена.")
        except Exception:
            logger.exception("Критичний збій під час виконання check_all_prices")
            sys.exit(1)

    else:
        logger.error(f"Запуск відхилено: Невідомий режим '{mode}'. Доступні режими: 'bot' або 'check'")
        sys.exit(1)

if __name__ == "__main__":
    main()
