import os
import sqlite3
from database import DatabaseManager
import requests
from logger_config import get_logger, UserContextAdapter
from services import PlaywrightParser, GeminiPriceExtractor

class PriceChecker:
    def __init__(self, db_manager: DatabaseManager, parser: PlaywrightParser, extractor: GeminiPriceExtractor):
        self.db_manager = db_manager
        self.parser = parser
        self.extractor = extractor
        self.base_logger = get_logger("checker")
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")

    def send_notification(self, user_id: int, url: str, old_price: float, new_price: float, currency: str) -> None:
        message = f"🔔 **Ціна змінилася!**\n\n🔗 [Посилання]({url})\n📉 Стара: {old_price} {currency}\n💰 Нова: {new_price} {currency}"
        telegram_url = f"https://telegram.org{self.telegram_token}/sendMessage"
        payload = {"chat_id": user_id, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
        
        logger = UserContextAdapter(self.base_logger.logger, {"user_id": user_id})
        try:
            response = requests.post(telegram_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"📣 Сповіщення успішно надіслано для {url}")
        except requests.RequestException:
            logger.exception(f"❌ Помилка мережі Telegram API при надсиланні сповіщення для {url}")

    def check_all_prices(self, target_user_id: int = None) -> None:
        self.base_logger.info("🚀 Запуск планової перевірки цін через об'єктний сервіс...")
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            # Dynamically append WHERE filter constraints to optimize SQL execution performance
            if target_user_id:
                self.base_logger.info(f"Scoping query targeting specific context filters for User ID: {target_user_id}")
                cursor.execute("SELECT id, user_id, url, last_price FROM products WHERE user_id = ?", (target_user_id,))
            else:
                self.base_logger.info("Executing comprehensive global system database table crawl workflow")
                cursor.execute("SELECT id, user_id, url, last_price FROM products")

            products = cursor.fetchall()
            self.base_logger.info(f"Database scan query returned exactly {len(products)} tracking elements.")
        except sqlite3.Error:
            self.base_logger.exception("Database cursor operation failed during target mapping fetching tasks")
            return

        for prod_id, user_id, url, last_price in products:
            logger = UserContextAdapter(self.base_logger.logger, {"user_id": user_id})
            logger.info(f"🔍 Початок обробки товару ID {prod_id}: {url}")
            
            try:
                # Викликаємо методи впроваджених сервісів
                page_text = self.parser.get_clean_text(url, logger)
                price_info = self.extractor.extract_price(page_text, logger)
            except Exception:
                logger.exception(f"💥 Системний збій об'єктного пайплайну для товару ID {prod_id}")
                continue
            
            if price_info and price_info.get("price", 0) > 0:
                new_price = price_info["price"]
                currency = price_info["currency"]
                
                if last_price == 0:
                    cursor.execute("UPDATE products SET last_price = ? WHERE id = ?", (new_price, prod_id))
                    conn.commit()
                    logger.info(f"✅ Первинна фіксація ціни для ID {prod_id}: {new_price} {currency}")
                elif new_price != last_price:
                    self.send_notification(user_id, url, last_price, new_price, currency)
                    cursor.execute("UPDATE products SET last_price = ? WHERE id = ?", (new_price, prod_id))
                    conn.commit()
                    logger.info(f"🎉 Ціна змінилася для ID {prod_id}: з {last_price} на {new_price} {currency}")
                else:
                    logger.info(f"💤 Ціна для ID {prod_id} стабільна ({last_price} {currency}).")
            else:
                logger.warning(f"⚠️ Не вдалося розпізнати ціну для ID {prod_id}.")
                
        conn.close()
        self.base_logger.info("🏁 Планову перевірку цін успішно завершено.")
