import os
import time
import telebot
import requests
import threading
from flask import Flask

# توكن البوت
BOT_TOKEN = os.getenv("BOT_TOKEN", "8047115821:AAEaBiEbkRkbfcLEF6JszlKi9Hm3chjGN5U")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# هاندلر استقبال الملفات
@bot.message_handler(content_types=['audio', 'voice', 'document', 'video', 'photo'])
def send_direct_url(message):
    try:
        # لو صورة: بناخد آخر واحدة (أعلى جودة)
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        else:
            file_id = getattr(message, message.content_type).file_id

        # نجيب معلومات الملف
        resp = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id}
        )
        data = resp.json()
        if not data.get("ok"):
            bot.reply_to(message, f"❌ حصل خطأ: {data}")
            return

        file_path = data["result"]["file_path"]

        # نبني الرابط المباشر المؤقت
        direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        # نرد على المستخدم بالرابط
        bot.reply_to(message, f"✅ الرابط المباشر (صالح لفترة قصيرة):\n{direct_url}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# صفحة افتراضية للـ health check
@app.route("/")
def home():
    return "Bot is running!", 200

# تشغيل البوت في Thread منفصل
def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Error in polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
