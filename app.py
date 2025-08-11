from flask import Flask, request
from telebot import TeleBot, types
from telethon import TelegramClient
import threading

# ===== إعداد التوكن والـ API =====
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"

WEBHOOK_URL = "https://mysterious-sapphira-yuag-7830d5f3.koyeb.app/webhook"

bot = TeleBot(BOT_TOKEN)
client = TelegramClient('session_name', API_ID, API_HASH)

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running ✅", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بيك! البوت شغال بالويب هوك ✅")

async def start_telethon():
    await client.start()
    print("[DEBUG] Telethon connected and authorized")

def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("[INFO] Webhook set successfully ✅")

if __name__ == '__main__':
    threading.Thread(target=lambda: client.loop.run_until_complete(start_telethon())).start()
    threading.Timer(2.0, setup_webhook).start()
    app.run(host='0.0.0.0', port=8000)
