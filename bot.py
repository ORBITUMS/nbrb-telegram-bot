import os
import requests
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.error import Conflict, RetryAfter
from datetime import datetime

# Безопасное получение токена из переменных окружения
TELEGRAM_TOKEN = os.environ['TG_TOKEN']
NBRB_API_URL = "https://api.nbrb.by/exrates/rates/USD?parammode=2"

# Health check сервер для Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    """Запуск HTTP-сервера для health checks"""
    server = HTTPServer(('0.0.0.0', 10000), HealthHandler)
    print(f"🩺 Health check сервер запущен на порту 10000")
    server.serve_forever()

def get_currency_rate():
    try:
        response = requests.get(NBRB_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = data['Cur_OfficialRate']
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        return f"🇺🇸 Курс доллара НБРБ\nна {date_str}:\n\n1 USD = {rate} BYN"
    except Exception as e:
        return f"⚠️ Ошибка при получении курса: {str(e)}"

async def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    welcome_msg = (
        f"Привет, {user.first_name}! 👋\n"
        "Я бот для отслеживания курса доллара от Нацбанка РБ.\n\n"
        "Просто нажми /rate чтобы получить текущий курс"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_msg)
    await send_rate(update, context)

async def rate_command(update: Update, context: CallbackContext):
    await send_rate(update, context)

async def send_rate(update: Update, context: CallbackContext):
    rate_msg = get_currency_rate()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=rate_msg)

async def reset_webhook():
    """Сброс всех предыдущих подключений"""
    async with Application.builder().token(TELEGRAM_TOKEN).build() as temp_app:
        await temp_app.bot.delete_webhook(drop_pending_updates=True)
        print("✅ Все предыдущие соединения сброшены")

def main():
    print("="*50)
    print("🛡️ Безопасный запуск: токен получен из переменных окружения")
    print("🟢 Инициализация бота...")
    print("="*50)
    
    # Запуск health check сервера в отдельном потоке
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Инициализация бота
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("rate", rate_command))
    
    # Запуск бота
    run_bot(application)

def run_bot(application):
    try:
        # Сброс предыдущих соединений
        asyncio.run(reset_webhook())
        
        print("🔐 Установка безопасного подключения к Telegram...")
        application.run_polling(
            drop_pending_updates=True,
            connect_timeout=60,
            read_timeout=60,
            bootstrap_retries=3
        )
        print("✅ Бот работает в безопасном режиме")
        
    except Conflict:
        print("⚠️ Обнаружен конфликт подключений. Перезапуск через 30 сек...")
        time.sleep(30)
        run_bot(application)
    except Exception as e:
        print(f"⛑️ Восстановление после ошибки: {e}")
        time.sleep(15)
        run_bot(application)

if __name__ == "__main__":
    import time
    main()
