import os
import json
import sys
import sqlite3
from bs4 import BeautifulSoup
import requests
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# Ініціалізація клієнта Gemini
client = genai.Client()

# Зчитуємо токен із змінних оточення
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN:
    print("❌ Помилка: Змінна TELEGRAM_BOT_TOKEN не знайдена в системі!")
    sys.exit(1)

def get_page_text(url):
    """Запускає справжній браузер у фоні для обходу захисту сайту"""
    try:
        with sync_playwright() as p:
            # Запускаємо браузер у прихованому режимі
            browser = p.chromium.launch(headless=True)
            
            # Створюємо контекст з налаштуваннями звичайного ПК
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="uk-UA"
            )
            page = context.new_page()
            
            # Переходимо на сайт та чекаємо, поки вщухне мережева активність
            print("⏳ Завантажую сторінку через браузер...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Забираємо згенерований HTML-код сторінки
            html_content = page.content()
            browser.close()
            
            # Очищаємо від HTML-сміття
            soup = BeautifulSoup(html_content, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                element.decompose()
                
            return " ".join(soup.get_text().split())
    except Exception as e:
        print(f"❌ Помилка Playwright для {url}: {e}")
        return None

def extract_price_with_llm(html_text):
    if not html_text:
        return None

    prompt = f"""
    Проаналізуй текст сторінки інтернет-магазину та знайди актуальну ціну товару.
    Ігноруй стару (перекреслену) ціну, якщо є знижка. Знайди саме ту ціну, за яку можна купити товар зараз.
    
    Текст сторінки:
    {html_text[:15000]}
    """

    try:
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
        return data if data["price"] > 0 else None
    except Exception as e:
        print(f"Помилка ШІ: {e}")
        return None

def send_notification(user_id, url, old_price, new_price, currency):
    message = f"🔔 **Ціна змінилася!**\n\n" \
              f"🔗 [Посилання на товар]({url})\n" \
              f"📉 Стара ціна: {old_price} {currency}\n" \
              f"💰 Нова ціна: {new_price} {currency}"
    
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": user_id, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(telegram_url, json=payload)

def check_all_prices():
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_id, url, last_price FROM products")
    products = cursor.fetchall()
    
    for prod_id, user_id, url, last_price in products:
        print(f"Перевіряю товар: {url}")
        
        page_text = get_page_text(url)
        price_info = extract_price_with_llm(page_text)
        
        if price_info:
            new_price = price_info["price"]
            currency = price_info["currency"]
            
            if last_price == 0:
                cursor.execute("UPDATE products SET last_price = ? WHERE id = ?", (new_price, prod_id))
                conn.commit()
                print(f"✅ Перший запис ціни для товару: {new_price} {currency}")
            elif new_price != last_price:
                send_notification(user_id, url, last_price, new_price, currency)
                cursor.execute("UPDATE products SET last_price = ? WHERE id = ?", (new_price, prod_id))
                conn.commit()
                print(f"🎉 Ціна змінилася з {last_price} на {new_price}")
            else:
                print("💤 Ціна не змінилася.")
        else:
            print(f"❌ Не вдалося розпізнати ціну для {url}")
            
    conn.close()
