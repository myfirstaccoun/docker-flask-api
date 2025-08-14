from telethon.sessions import StringSession
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

# Event loop مخصص لـ Telethon
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# عميل Telethon
client = TelegramClient('session_name', API_ID, API_HASH, loop=loop)
client.start()

# مسار Flask لإرسال رسالة إلى البوت
@app.route('/', methods=['GET'])
def send_message():
    message = request.args.get('message', 'Hello from Flask+Telethon via GET!')

    async def send():
        await client.send_message(BOT_YT, message)

    loop.run_until_complete(send())

    return jsonify({'status': 'message sent', 'to': BOT_YT, 'message': message})

# أوامر Telebot
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "أهلاً! هذا البوت يشتغل مع Telethon و Flask في نفس الوقت 🚀")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    bot.reply_to(message, f"انت كتبت: {message.text}")

# تشغيل Telebot في ثريد منفصل
def run_telebot():
    bot.polling(none_stop=True)

# تشغيل Flask في ثريد منفصل
def run_flask():
    app.run(debug=True, use_reloader=False)

# تشغيل الكل
if __name__ == '__main__':
    threading.Thread(target=run_telebot).start()
    threading.Thread(target=run_flask).start()
