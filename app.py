import os
import threading
from flask import Flask, request
from telebot import TeleBot
from telethon import TelegramClient

# ===== إعداد التوكن والـ API =====
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"

WEBHOOK_URL = "https://mysterious-sapphira-yuag-7830d5f3.koyeb.app/webhook"

# ===== تهيئة TeleBot (للويب هوك) =====
bot = TeleBot(BOT_TOKEN)

# ===== تهيئة Telethon (لـ session_name.session) =====
client = TelegramClient('session_name', API_ID, API_HASH)

# ===== Flask App =====
app = Flask(__name__)

# ===== مسار استقبال الـ Webhook =====
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = bot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

# ===== مثال على أمر بوت =====
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بيك! البوت شغال بالويب هوك ✅")

# ===== تشغيل Telethon =====
async def start_telethon():
    await client.start()
    print("[DEBUG] Telethon connected and authorized")

# ===== وظيفة لضبط الـ webhook بعد تشغيل السيرفر =====
def setup_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        print("[INFO] Webhook set successfully ✅")
    except Exception as e:
        print(f"[ERROR] Failed to set webhook: {e}")

# ===== نقطة البداية =====
if __name__ == '__main__':
    # تشغيل Telethon في Thread منفصل
    threading.Thread(target=lambda: client.loop.run_until_complete(start_telethon())).start()
    
    # ضبط الويب هوك بعد ثانيتين من بدء السيرفر
    threading.Timer(2.0, setup_webhook).start()

    # تشغيل Flask (Gunicorn هيشغله في الإنتاج)
    app.run(host='0.0.0.0', port=8000)
