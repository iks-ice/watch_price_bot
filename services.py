import os
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types
from logger_config import UserContextAdapter

class PlaywrightParser:
    """Сервіс для рендерингу сторінок та очищення HTML-коду."""
    
    def __init__(self, user_agent: str = None):
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    def get_clean_text(self, url: str, logger: UserContextAdapter) -> str | None:
        try:
            with sync_playwright() as p:
                logger.info("⏳ Запуск Chromium через Playwright...")
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.user_agent,
                    viewport={"width": 1920, "height": 1080},
                    locale="uk-UA"
                )
                page = context.new_page()
                
                logger.info(f"🌐 Сканування лінка: {url}")
                page.goto(url, wait_until="networkidle", timeout=30000)
                html_content = page.content()
                browser.close()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    element.decompose()
                    
                return " ".join(soup.get_text().split())
        except Exception as e:
            logger.error(f"❌ Помилка Playwright сервісу: {e}")
            return None


class GeminiPriceExtractor:
    """Сервіс для структурованого аналізу тексту за допомогою LLM."""
    
    def __init__(self):
        # Explicitly fetch the token from environment and inject it into the client configuration context
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Critical configuration failure: GEMINI_API_KEY variable is missing from environment context.")
            
        self.client = genai.Client(api_key=api_key)

    def extract_price(self, html_text: str, logger: UserContextAdapter) -> dict | None:
        if not html_text:
            return None

        prompt = f"""
        Проаналізуй текст сторінки інтернет-магазину та знайди актуальну ціну товару.
        Ігноруй стару (перекреслену) ціну, якщо є знижка. Знайди саме ту ціну, за яку можна купити товар зараз.
        
        Текст сторінки:
        {html_text[:15000]}
        """
        try:
            logger.info("🧠 Запит до Gemini 2.5 Flash сервісу...")
            response = self.client.models.generate_content(
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
            logger.error(f"❌ Помилка Gemini сервісу: {e}")
            return None
