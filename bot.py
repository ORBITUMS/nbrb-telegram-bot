import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from datetime import datetime

# Автопоиск токена
TELEGRAM_TOKEN = os.environ.get('TG_TOKEN')
if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = "8250242729:AAEkH3O9ZJftDj1wtG84lckLB2VVnd3bgNs"  # ваш токен
    print("⚠️ Внимание: используется токен из кода!")

NBRB_API_URL = "https://api.nbrb.by/exrates/rates/USD?parammode=2"

def get_currency_rate():
    try:
        response = requests.get(NBRB_API_URL)
        response.raise_for_status()
        data = response.json()
        rate = data['Cur_OfficialRate']
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        return f"🇺🇸 Курс доллара НБРБ\nна {date_str}:\n\n1 USD = {rate} BYN"
    except Exception as e:
        return f"⚠️ Ошибка: {str(e)}"

def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    welcome_msg = f"Привет, {user.first_name}! 👋\nЯ бот для отслеживания курса доллара от Нацбанка РБ.\n\n"
    welcome_msg += "Просто нажми /rate чтобы получить текущий курс"
    context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_msg)
    rate_msg = get_currency_rate()
    context.bot.send_message(chat_id=update.effective_chat.id, text=rate_msg)

def rate_command(update: Update, context: CallbackContext):
    rate_msg = get_currency_rate()
    context.bot.send_message(chat_id=update.effective_chat.id, text=rate_msg)

def main():
    print("🟢 Бот запущен и работает 24/7")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("rate", rate_command))
    
    application.run_polling()

if __name__ == "__main__":
    main()
