import sqlite3
import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logger_config import get_logger, UserContextAdapter

base_logger = get_logger("bot")
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))

def init_db():
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            last_price REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username

    logger = UserContextAdapter(base_logger.logger, {"user_id": user_id})
    logger.info("Запит команди /start")

    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

    bot.reply_to(message, "👋 Привіт! Надішліть мені посилання на товар, і я додам його до вашого списку моніторингу.")

@bot.message_handler(commands=["list"])
def list_products(message):
    user_id = message.from_user.id
    logger = UserContextAdapter(base_logger.logger, {"user_id": user_id})
    logger.info("Запит команди /list")
    
    try:
        conn = sqlite3.connect("tracker.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, url, last_price FROM products WHERE user_id = ?", (user_id,))
        products = cursor.fetchall()
        conn.close()
    except sqlite3.Error:
        logger.exception("Помилка роботи з БД при виклику /list")
        bot.send_message(message.chat.id, "❌ Помилка при отриманні списку.")
        return
        
    if not products:
        logger.info("Список товарів порожній")
        bot.send_message(message.chat.id, "📭 Ваш список відстеження порожній.")
        return
        
    bot.send_message(message.chat.id, "📋 **Ваші товари на відстеженні:**", parse_mode="Markdown")
    
    for prod_id, url, last_price in products:
        try:
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")
        except Exception:
            domain = "Посилання"
            
        text = f"🔗 [{domain}]({url})\n💰 Поточна ціна: {last_price if last_price else 'Не визначено'}"
        
        # Створюємо Inline-кнопку
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="❌ Видалити", callback_data=f"delete_{prod_id}"))
        
        bot.send_message(
            message.chat.id, 
            text, 
            reply_markup=keyboard, 
            parse_mode="Markdown", 
            disable_web_page_preview=True
        )
    logger.info(f"Успішно виведено список із {len(products)} товарів.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def process_delete_product(call):
    prod_id = int(call.data.split("_")[-1])
    user_id = call.from_user.id
    
    logger = UserContextAdapter(base_logger.logger, {"user_id": user_id})
    logger.info(f"Запит на видалення товару ID {prod_id}")
    
    try:
        conn = sqlite3.connect("tracker.db")
        cursor = conn.cursor()
        
        # Перевірка прав власності на запис
        cursor.execute("SELECT id FROM products WHERE id = ? AND user_id = ?", (prod_id, user_id))
        product = cursor.fetchone()
        
        if product:
            cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
            conn.commit()
            logger.info(f"Товар ID {prod_id} успішно видалено.")
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🗑️ Товар видалено зі списку відстеження."
            )
            bot.answer_callback_query(call.id, "Видалено!")
        else:
            logger.warning(f"Спроба несанкціонованого видалення товару ID {prod_id}")
            bot.answer_callback_query(call.id, "Помилка: товар не знайдено або він не ваш.", show_alert=True)
            
        conn.close()
    except sqlite3.Error:
        logger.exception(f"Помилка бази даних під час видалення товару ID {prod_id}")
        bot.answer_callback_query(call.id, "Внутрішня помилка БД.", show_alert=True)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    url = message.text.strip()

    logger = UserContextAdapter(base_logger.logger, {"user_id": user_id})
    logger.info("Додавання товару")

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "❌ Будь ласка, надішліть коректне посилання (з http:// або https://)")
        return

    try:
        conn = sqlite3.connect("tracker.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username))
        cursor.execute("INSERT INTO products (user_id, url) VALUES (?, ?)", (user_id, url))
        conn.commit()
        bot.reply_to(message, "✅ Товар успішно додано до вашого списку моніторингу!")
        logger.info(f"Товар успішно додано {url}")
    except sqlite3.IntegrityError:
        bot.reply_to(message, "ℹ️ Ви вже додавали це посилання раніше.")
    except Exception as e:
        bot.reply_to(message, f"❌ Сталася помилка: {e}")
    finally:
        conn.close()
