import os
import requests
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.error import Conflict
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

def main():
    print("🟢 Запуск бота...")
    
    # Создаем Application с обработкой конфликтов
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("rate", rate_command))
    
    try:
        # Запускаем бота с защитой от конфликтов
        print("⏳ Подключение к Telegram API...")
        application.run_polling(
            drop_pending_updates=True,
            close_loop=False,
            allowed_updates=Update.ALL_TYPES,
            connect_timeout=30,
            read_timeout=30
        )
        print("🟢 Бот успешно запущен")
    except Conflict as e:
        print(f"🔴 Критическая ошибка: {e}")
        print("⚠️ Убедитесь, что бот не запущен в других местах (PythonAnywhere, локальный компьютер)")
        print("🔄 Попытка перезапуска через 30 секунд...")
        time.sleep(30)
        main()  # Рекурсивный перезапуск
    except Exception as e:
        print(f"⚠️ Непредвиденная ошибка: {e}")
        print("🔄 Перезапуск через 10 секунд...")
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
