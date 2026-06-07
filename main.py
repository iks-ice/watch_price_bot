import sys
import os
from dotenv import load_dotenv

# Автоматично завантажуємо змінні з файлу .env у систему
load_dotenv()

# Імпортуємо логіку з інших файлів вже ПІСЛЯ завантаження .env
from bot import init_db, bot as telegram_bot
from price_checker import check_all_prices

def main():
    # Ініціалізуємо базу даних
    init_db()

    # Перевіряємо аргументи командного рядка
    if len(sys.argv) < 2:
        print("❌ Помилка: Вкажіть режим запуску.")
        print("Використання:")
        print("  python main.py bot     - запуск Telegram-бота")
        print("  python main.py check   - запуск одноразової перевірки цін")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "bot":
        print("🚀 Запуск Telegram-бота...")
        print("Бот працює локально та чекає на ваші лінки.")
        telegram_bot.infinity_polling()

    elif mode == "check":
        print("🔄 Запуск перевірки цін за допомогою Gemini LLM...")
        check_all_prices()
        print("✅ Перевірка всіх цін завершена!")

    else:
        print(f"❌ Невідомий режим: '{mode}'")
        print("Доступні режими: 'bot' або 'check'")
        sys.exit(1)

if __name__ == "__main__":
    main()
