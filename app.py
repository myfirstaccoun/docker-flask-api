
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

# Event loop خاص بـ Telethon
loop = asyncio.new_event_loop()
client = TelegramClient('session_name', API_ID, API_HASH, loop=loop)

# تشغيل Telethon في الخلفية
def run_telethon():
    loop.run_until_complete(client.start())
    loop.run_forever()

threading.Thread(target=run_telethon, daemon=True).start()

# مسار Flask
@app.route('/', methods=['GET'])
def send_message():
    message = request.args.get('message', 'Hello from Flask+Telethon via GET!')

    async def send():
        await client.send_message(BOT_YT, message)

    asyncio.run_coroutine_threadsafe(send(), loop)

    return jsonify({'status': 'message sent', 'to': BOT_YT, 'message': message})

# أوامر Telebot
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "مرحباً! البوت شغال مع Telethon و Flask مع بعض 🚀")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, f"انت كتبت: {message.text}")

# تشغيل Telebot في thread منفصل
def run_telebot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"خطأ في Telebot: {e}")

# تشغيل Flask في thread منفصل
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_telebot, daemon=True).start()
    run_flask()
