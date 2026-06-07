import os
import json
import sqlite3
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
# Імпортуємо новий офіційний SDK для Gemini
from google import genai
from google.genai import types

# Імпортуємо налаштовану архітектуру логування
from logger_config import get_logger, UserContextAdapter

# Базовий логгер для системних подій модуля чекера
base_logger = get_logger("checker")

# Ініціалізуємо клієнт Gemini. Він автоматично підтягне GEMINI_API_KEY з .env
client = genai.Client()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


def get_page_text(url: str, logger: UserContextAdapter) -> str | None:
    """Запускає Chromium у фоні за допомогою Playwright для обходу захисту сайту."""
    try:
        with sync_playwright() as p:
            logger.info("⏳ Запуск безголового браузера Playwright...")
            browser = p.chromium.launch(headless=True)
            
            # Імітуємо поведінку реального користувача
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="uk-UA"
            )
            page = context.new_page()
            
            logger.info(f"🌐 Перехід на сторінку: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            html_content = page.content()
            browser.close()
            
            # Очищаємо сторінку від HTML-шуму для економії токенів Gemini
            soup = BeautifulSoup(html_content, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                element.decompose()
                
            # Повертаємо чистий нормалізований текст сторінки
            return " ".join(soup.get_text().split())
            
    except Exception as e:
        logger.error(f"❌ Критична помилка Playwright для {url}: {e}")
        return None


def extract_price_with_llm(html_text: str, logger: UserContextAdapter) -> dict | None:
    """Аналізує очищений текст за допомогою Gemini 2.5 Flash та повертає структурований JSON."""
    if not html_text:
        return None

    prompt = f"""
    Проаналізуй текст сторінки інтернет-магазину та знайди актуальну ціну товару.
    Ігноруй стару (перекреслену) ціну, якщо є знижка. Знайди саме ту ціну, за яку можна купити товар зараз.
    
    Текст сторінки:
    {html_text[:15000]}
    """

    try:
        logger.info("🧠 Надсилання запиту до Gemini 2.5 Flash (Structured Outputs)...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "price": types.Schema(type=types.Type.INTEGER, description="Тільки число ціни."),
                        "currency": types.Schema(type=types.Type.STRING, description="Валюта, наприклад: UAH, USD")
                    },
                    required=["price", "currency"]
                ),
            ),
        )
        
        data = json.loads(response.text)
        return data if data.get("price", 0) > 0 else None
        
    except Exception as e:
        logger.error(f"❌ Помилка інтерфейсу ШІ Gemini: {e}")
        return None


def send_notification(user_id: int, url: str, old_price: float, new_price: float, currency: str) -> None:
    """Надсилає структуроване сповіщення про зміну ціни у Telegram користувача."""
    message = f"🔔 **Ціна змінилася!**\n\n🔗 [Посилання]({url})\n📉 Стара: {old_price} {currency}\n💰 Нова: {new_price} {currency}"
    telegram_url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": user_id, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    
    logger = UserContextAdapter(base_logger.logger, {"user_id": user_id})
    
    try:
        response = requests.post(telegram_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"📣 Сповіщення успішно надіслано для {url}")
    except requests.RequestException:
        logger.exception(f"❌ Помилка мережі Telegram API при надсиланні сповіщення для {url}")


def check_all_prices() -> None:
    """Головний цикл Cron: отримує товари з БД, викликає парсинг, ШІ-аналіз та оновлює стани."""
    base_logger.info("🚀 Запуск планової перевірки цін...")
    
    try:
        conn = sqlite3.connect("tracker.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, url, last_price FROM products")
        products = cursor.fetchall()
        base_logger.info(f"З бази даних успішно зчитано {len(products)} товарів.")
    except sqlite3.Error:
        base_logger.exception("Критична помилка ініціалізації або читання SQLite")
        return

    for prod_id, user_id, url, last_price in products:
        # Ініціалізуємо контекстний логгер під користувача, чий товар обробляється
        logger = UserContextAdapter(base_logger.logger, {"user_id": user_id})
        logger.info(f"🔍 Початок обробки товару ID {prod_id}: {url}")
        
        try:
            # Передаємо logger всередину, щоб бачити контекст юзера навіть у підфункціях
            page_text = get_page_text(url, logger)
            price_info = extract_price_with_llm(page_text, logger)
        except Exception:
            logger.exception(f"💥 Системний збій пайплайну (Playwright/Gemini) для товару ID {prod_id}")
            continue
        
        if price_info and price_info.get("price", 0) > 0:
            new_price = price_info["price"]
            currency = price_info["currency"]
            
            if last_price == 0:
                cursor.execute("UPDATE products SET last_price = ? WHERE id = ?", (new_price, prod_id))
                conn.commit()
                logger.info(f"✅ Первинна фіксація ціни для ID {prod_id}: {new_price} {currency}")
            elif new_price != last_price:
                send_notification(user_id, url, last_price, new_price, currency)
                cursor.execute("UPDATE products SET last_price = ? WHERE id = ?", (new_price, prod_id))
                conn.commit()
                logger.info(f"🎉 Ціна змінилася для ID {prod_id}: з {last_price} на {new_price} {currency}")
            else:
                logger.info(f"💤 Ціна для ID {prod_id} стабільна ({last_price} {currency}).")
        else:
            logger.warning(f"⚠️ Не вдалося розпізнати ціну для ID {prod_id}. Отримано дані: {price_info}")
            
    conn.close()
    base_logger.info("🏁 Планову перевірку цін успішно завершено.")
