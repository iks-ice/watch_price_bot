import os
import sqlite3
import sys
import telebot

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ Помилка: Змінна TELEGRAM_BOT_TOKEN не знайдена в системі!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            last_price INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE(user_id, url)
        )
    """)
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username

    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

    bot.reply_to(message, "👋 Привіт! Надішліть мені посилання на товар, і я додам його до вашого списку моніторингу.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    url = message.text.strip()

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
    except sqlite3.IntegrityError:
        bot.reply_to(message, "ℹ️ Ви вже додавали це посилання раніше.")
    except Exception as e:
        bot.reply_to(message, f"❌ Сталася помилка: {e}")
    finally:
        conn.close()
