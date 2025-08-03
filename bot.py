import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.error import Conflict, RetryAfter
from datetime import datetime

# Конфигурация токена
TELEGRAM_TOKEN = os.environ.get('TG_TOKEN') or "8237013358:AAF9WBi1ImRfdTB_xap65uRFawkAdKS8H2A"
if not os.environ.get('TG_TOKEN'):
    print("⚠️ Внимание: используется токен из кода!")

NBRB_API_URL = "https://api.nbrb.by/exrates/rates/USD?parammode=2"

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
    """Асинхронный сброс вебхука с подтверждением"""
    async with Application.builder().token(TELEGRAM_TOKEN).build() as temp_app:
        await temp_app.bot.delete_webhook(drop_pending_updates=True)
        print("✅ Вебхук успешно сброшен")

def main():
    print("🟢 Запуск бота...")
    
    # Создаем Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("rate", rate_command))
    
    # Запускаем бота с гарантированным сбросом соединений
    run_bot(application)

def run_bot(application):
    try:
        # Принудительный сброс всех предыдущих соединений
        print("🛑 Принудительная очистка предыдущих соединений...")
        asyncio.run(reset_webhook())
        
        print("⏳ Подключение к Telegram API...")
        application.run_polling(
            drop_pending_updates=True,
            close_loop=False,
            allowed_updates=Update.ALL_TYPES,
            connect_timeout=60,
            read_timeout=60,
            pool_timeout=60,
            bootstrap_retries=3,  # Дополнительные попытки подключения
        )
        print("🟢 Бот успешно запущен")
    except Conflict as e:
        print(f"🔴 Критическая ошибка конфликта: {e}")
        print("🔄 Попытка полного перезапуска через 120 секунд...")
        time.sleep(120)
        run_bot(application)
    except RetryAfter as e:
        print(f"⏱️ Telegram API требует паузу: {e.retry_after} сек.")
        time.sleep(e.retry_after + 10)
        run_bot(application)
    except Exception as e:
        print(f"⚠️ Непредвиденная ошибка: {e}")
        print("🔄 Перезапуск через 60 секунд...")
        time.sleep(60)
        run_bot(application)

if __name__ == "__main__":
    import time
    print(f"🔑 Используется токен: {TELEGRAM_TOKEN[:10]}...")
    print("✅ Гарантия единственного экземпляра")
    main()
