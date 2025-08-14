from telethon import TelegramClient
from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
import threading
import telebot

# إعدادات Telethon
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_YT = '@BotYouTubeDownloadBot'

# إعدادات Telebot
TELEBOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"
bot = telebot.TeleBot(TELEBOT_TOKEN)

# Flask
app = Flask(__name__)
CORS(app)

# Telethon
client = TelegramClient('session_name', API_ID, API_HASH)

# Telebot
bot = telebot.AsyncTeleBot(TELEBOT_TOKEN)

# إلغاء أي webhook موجود
bot.remove_webhook()

@app.route('/', methods=['GET'])
def send_message():
    message = request.args.get('message', 'Hello!')
    async def send():
        await client.send_message(BOT_YT, message)
    asyncio.run(send())
    return jsonify({'status': 'message sent', 'to': BOT_YT, 'message': message})

# أوامر Telebot
@bot.message_handler(commands=['start'])
async def start_command(message):
    await bot.reply_to(message, "مرحباً! النظام بيشتغل بأقل استهلاك 🚀")

@bot.message_handler(func=lambda m: True)
async def echo_all(message):
    await bot.reply_to(message, f"انت كتبت: {message.text}")

async def main():
    await client.start()
    await asyncio.gather(
        bot.infinity_polling(timeout=60, skip_pending=True),
    )

if __name__ == '__main__':
    import threading
    # تشغيل Flask في thread
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False), daemon=True).start()
    asyncio.run(main())
