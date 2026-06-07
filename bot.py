import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logger_config import get_logger, UserContextAdapter
from database import DatabaseManager

class TelegramPriceBot:
    """Enterprise OOP service container managing Telegram Bot events and commands."""
    
    def __init__(self, token: str, db_manager: DatabaseManager, price_checker = None):
        if not token:
            raise ValueError("Telegram Bot token must be explicitly provided.")
            
        self.bot = telebot.TeleBot(token)
        self.db = db_manager
        self.checker = price_checker
        self.base_logger = get_logger("bot")
        
        # Register handler hooks dynamically to preserve explicit self reference context
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Binds incoming routing updates into the class method callbacks."""
        self.bot.register_message_handler(self.send_welcome, commands=['start'])
        self.bot.register_message_handler(self.list_products, commands=['list'])
        self.bot.register_message_handler(self.force_check_products, commands=['check'])
        self.bot.register_callback_query_handler(self.process_delete_product, func=lambda call: call.data.startswith("delete_"))
        self.bot.register_message_handler(self.handle_message, func=lambda message: True)

    def start_polling(self) -> None:
        """Starts the infinite network updates polling daemon."""
        self.base_logger.info("Starting Telegram Bot listener via Infinity Polling engine...")
        self.bot.infinity_polling()

    def send_welcome(self, message: telebot.types.Message) -> None:
        user_id = message.from_user.id
        username = message.from_user.username
        logger = UserContextAdapter(self.base_logger.logger, {"user_id": user_id})
        logger.info("Invoked /start command wrapper")

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
                conn.commit()
            self.bot.reply_to(message, "👋 Привіт! Надішліть мені посилання на товар, і я додам його до вашого списку моніторингу.")
        except Exception:
            logger.exception("Failed to store user profile update upon /start command execution")
            self.bot.reply_to(message, "❌ Сталася внутрішня помилка при реєстрації профілю.")

    def list_products(self, message: telebot.types.Message) -> None:
        user_id = message.from_user.id
        logger = UserContextAdapter(self.base_logger.logger, {"user_id": user_id})
        logger.info("Invoked /list products summary command")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, url, last_price FROM products WHERE user_id = ?", (user_id,))
                products = cursor.fetchall()
        except Exception:
            logger.exception("Failed to query active tracking records from master table")
            self.bot.send_message(message.chat.id, "❌ Помилка при отриманні списку товарів.")
            return
            
        if not products:
            logger.info("User monitoring catalog contains zero targets")
            self.bot.send_message(message.chat.id, "📭 Ваш список відстеження порожній.")
            return
            
        self.bot.send_message(message.chat.id, "📋 **Ваші товари на відстеженні:**", parse_mode="Markdown")
        
        for prod_id, url, last_price in products:
            try:
                # Safe domain string resolution extraction
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
            except Exception:
                domain = "Посилання"
                
            text = f"🔗 [{domain}]({url})\n💰 Поточна ціна: {last_price if last_price else 'Не визначено'}"
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(text="❌ Видалити", callback_data=f"delete_{prod_id}"))
            
            self.bot.send_message(
                message.chat.id, 
                text, 
                reply_markup=keyboard, 
                parse_mode="Markdown", 
                disable_web_page_preview=True
            )
        logger.info(f"Successfully rendered data blocks for {len(products)} tracks.")

    def process_delete_product(self, call: telebot.types.CallbackQuery) -> None:
        prod_id = int(call.data.split("_")[-1])
        user_id = call.from_user.id
        logger = UserContextAdapter(self.base_logger.logger, {"user_id": user_id})
        logger.info(f"Triggered product cancellation request for ID: {prod_id}")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Enforce server-side tenancy context validation (IDOR remediation)
                cursor.execute("SELECT id FROM products WHERE id = ? AND user_id = ?", (prod_id, user_id))
                product = cursor.fetchone()
                
                if product:
                    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
                    conn.commit()
                    logger.info(f"Successfully purged product instance ID: {prod_id}")
                    
                    self.bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="🗑️ Товар видалено зі списку відстеження."
                    )
                    self.bot.answer_callback_query(call.id, "Видалено!")
                else:
                    logger.warning(f"Unauthorized or invalid product deletion exploit vector blocked for target ID: {prod_id}")
                    self.bot.answer_callback_query(call.id, "Помилка: товар не знайдено або він не ваш.", show_alert=True)
        except Exception:
            logger.exception(f"Database core fault encountered during processing deletion on record ID: {prod_id}")
            self.bot.answer_callback_query(call.id, "Внутрішня помилка бази даних.", show_alert=True)

    def handle_message(self, message: telebot.types.Message) -> None:
        user_id = message.from_user.id
        url = message.text.strip()
        logger = UserContextAdapter(self.base_logger.logger, {"user_id": user_id})
        logger.info("Processing inbound uniform monitoring target registration link")

        if not (url.startswith("http://") or url.startswith("https://")):
            self.bot.reply_to(message, "❌ Будь ласка, надішліть коректне посилання (з http:// або https://)")
            return

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Safeguard cascading relationship updates
                cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username))
                cursor.execute("INSERT INTO products (user_id, url) VALUES (?, ?)", (user_id, url))
                conn.commit()
                
            self.bot.reply_to(message, "✅ Товар успішно додано до вашого списку моніторингу!")
            logger.info(f"Successfully added tracking line entry for target URL: {url}")
        except Exception as e:
            logger.exception("Failed to write new monitoring pipeline entry target to persistent schema storage")
            self.bot.reply_to(message, f"❌ Сталася помилка при збереженні: {e}")

    def force_check_products(self, message: telebot.types.Message) -> None:
        """Handles the /check command to run an immediate on-demand price evaluation for the specific user."""
        user_id = message.from_user.id
        logger = UserContextAdapter(self.base_logger.logger, {"user_id": user_id})
        logger.info("Invoked on-demand manual /check command routine")

        if not self.checker:
            logger.error("PriceChecker service dependency was not injected into the TelegramPriceBot container")
            self.bot.reply_to(message, "❌ Функція примусової перевірки наразі недоступна.")
            return

        # Send an immediate status update to avoid Telegram UI freezing during network operations
        status_msg = self.bot.reply_to(message, "⏳ Починаю примусову перевірку ваших товарів через Playwright та Gemini. Це може зайняти до хвилини...")

        try:
            # 3. Call the modified check method, specifying the current user context scope
            logger.info("Delegating execution context control over to the PriceChecker service instance")
            self.checker.check_all_prices(target_user_id=user_id)
            
            self.bot.edit_message_text(
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id,
                text="✅ Примусову перевірку ваших товарів завершено! Якщо ціни змінилися, ви отримали сповіщення."
            )
        except Exception:
            logger.exception("On-demand force price check execution pipeline crashed")
            self.bot.edit_message_text(
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id,
                text="❌ Під час примусової перевірки цін сталася критична помилка."
            )