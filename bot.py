import os
import sys
import requests
import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.error import Conflict, RetryAfter, TelegramError
from datetime import datetime
import pytz

# Проверка переменных окружения
def check_environment():
    """Проверяет обязательные переменные окружения"""
    required_vars = ['TG_TOKEN', 'PORT']
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
PORT = int(os.environ['PORT'])
CURRENCY_API_URL = "https://api.nbrb.by/exrates/rates?periodicity=0"

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
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    print(f"🩺 Health check сервер запущен на порту {PORT}")
    server.serve_forever()

def get_minsk_time():
    """Возвращает текущее время в Минске (UTC+3)"""
    minsk_tz = pytz.timezone('Europe/Minsk')
    return datetime.now(minsk_tz)

def format_currency_rate(currency_data):
    """Форматирует данные о валюте в читаемый вид"""
    rates = {
        'USD': {'symbol': '🇺🇸', 'name': 'Доллар США', 'scale': 1},
        'EUR': {'symbol': '🇪🇺', 'name': 'Евро', 'scale': 1},
        'RUB': {'symbol': '🇷🇺', 'name': 'Российских рублей', 'scale': 100}
    }
    
    formatted = ""
    for currency in currency_data:
        code = currency['Cur_Abbreviation']
        if code in rates:
            rate = currency['Cur_OfficialRate']
            scale = currency['Cur_Scale']
            symbol = rates[code]['symbol']
            name = rates[code]['name']
            final_rate = (rate * rates[code]['scale']) / scale
            formatted += f"{symbol} {rates[code]['scale']} {name} = {final_rate:.4f} BYN\n"
    
    return formatted.strip()

def get_currency_rates():
    """Получает курсы валют от НБРБ"""
    try:
        response = requests.get(CURRENCY_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Фильтруем нужные валюты
        currencies = [item for item in data if item['Cur_Abbreviation'] in ['USD', 'EUR', 'RUB']]
        
        if not currencies or len(currencies) < 3:
            return "⚠️ Не удалось получить данные по всем валютам"
        
        minsk_time = get_minsk_time()
        date_str = minsk_time.strftime("%d.%m.%Y %H:%M (Минск)")
        
        rates_text = format_currency_rate(currencies)
        return f"💱 Курсы валют НБРБ\nна {date_str}:\n\n{rates_text}"
    
    except Exception as e:
        return f"⚠️ Ошибка при получении курса: {str(e)}"

async def start_command(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_msg = (
        f"Привет, {user.first_name}! 👋\n"
        "Я бот для отслеживания курсов валют от Нацбанка РБ.\n\n"
        "Нажми кнопку ниже чтобы получить текущие курсы:"
    )
    
    # Создаем клавиатуру с кнопкой
    keyboard = [[InlineKeyboardButton("💱 Получить курсы", callback_data='get_rates')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_msg,
        reply_markup=reply_markup
    )

async def rate_command(update: Update, context: CallbackContext):
    """Обработчик команды /rate"""
    await send_rates(update, context)

async def send_rates(update: Update, context: CallbackContext):
    """Отправляет текущие курсы валют"""
    rates_msg = get_currency_rates()
    
    # Создаем клавиатуру для обновления
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data='refresh_rates')],
        [InlineKeyboardButton("ℹ️ О боте", callback_data='about')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=rates_msg,
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: CallbackContext):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'get_rates' or query.data == 'refresh_rates':
        # Удаляем предыдущее сообщение с кнопками
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
        except TelegramError:
            pass  # Если сообщение уже старое, пропускаем ошибку
        
        # Отправляем обновленные курсы
        await send_rates(update, context)
    
    elif query.data == 'about':
        about_msg = (
            "ℹ️ Бот курсов валют НБРБ\n\n"
            "Предоставляет актуальные курсы:\n"
            "- Доллара США (USD)\n"
            "- Евро (EUR)\n"
            "- 100 Российских рублей (RUB)\n\n"
            "Данные обновляются в режиме реального времени\n"
            "с сайта Национального Банка Республики Беларусь"
        )
        await query.edit_message_text(text=about_msg)

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
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("rate", rate_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
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
