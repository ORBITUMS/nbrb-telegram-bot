import os
import sys
import requests
import asyncio
import threading
import time  # Перенесён вверх
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.error import Conflict, RetryAfter, TelegramError
from datetime import datetime

# Улучшенная проверка переменных окружения
def check_environment():
    """Проверяет обязательные переменные окружения"""
    required_vars = ['TG_TOKEN', 'PORT']  # Добавлен PORT
    missing = [var for var in required_vars if var not in os.environ]
    
    if missing:
        print(f"❌ Критическая ошибка: отсутствуют переменные окружения: {', '.join(missing)}")
        print("\n📝 Инструкция по настройке на Render.com:")
        print("1. Перейдите в Dashboard -> ваш сервис")
        print("2. Выберите вкладку 'Environment'")
        print("3. Добавьте переменные:")
        print("   - Key: TG_TOKEN")
        print("   - Value: ваш_токен_бота")
        print("   - Key: PORT")
        print("   - Value: 10000")
        print("4. Нажмите 'Save Changes'")
        print("5. В разделе 'Advanced' добавьте:")
        print("   - Health Check Path: /health")
        print("6. Перезапустите сервис")
        sys.exit(1)

    print("✅ Все обязательные переменные окружения установлены")

# Проверяем переменные перед запуском
check_environment()

TELEGRAM_TOKEN = os.environ['TG_TOKEN']
PORT = int(os.environ['PORT'])  # Используем порт из переменной окружения
NBRB_API_URL = "https://api.nbrb.by/exrates/rates/USD?parammode=2"

# Health check сервер
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
    """Запуск HTTP-сервера для проверок работоспособности"""
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)  # Используем PORT
    print(f"🩺 Health check сервер запущен на порту {PORT}")
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
    await safe_send_message(context, update.effective_chat.id, welcome_msg)
    await send_rate(update, context)

async def rate_command(update: Update, context: CallbackContext):
    await send_rate(update, context)

async def send_rate(update: Update, context: CallbackContext):
    rate_msg = get_currency_rate()
    await safe_send_message(context, update.effective_chat.id, rate_msg)

async def safe_send_message(context: CallbackContext, chat_id: int, text: str):
    """Отправка сообщения с обработкой ошибок Telegram"""
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except RetryAfter as e:
        print(f"⚠️ Telegram API limit exceeded. Waiting {e.retry_after} seconds...")
        await asyncio.sleep(e.retry_after)
        await safe_send_message(context, chat_id, text)
    except TelegramError as e:
        print(f"⚠️ Telegram error: {e}")

def main():
    print("="*50)
    print(f"🚀 Запуск валютного бота на порту {PORT}")
    print("="*50)
    
    # Запуск health check сервера
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
        print("🔐 Установка защищенного подключения к Telegram...")
        application.run_polling(
            drop_pending_updates=True,
            read_timeout=60,
            bootstrap_retries=3,
            allowed_updates=Update.ALL_TYPES
        )
        print("✅ Бот успешно запущен и работает")
        
    except Conflict as e:
        print(f"⚠️ Обнаружен конфликт подключений: {e}. Перезапуск через 30 сек...")
        time.sleep(30)
        run_bot(application)
    except Exception as e:
        print(f"⛑️ Критическая ошибка: {e}. Перезапуск через 15 сек...")
        time.sleep(15)
        run_bot(application)

if __name__ == "__main__":
    main()
