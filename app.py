import telebot
import requests

BOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"  # من BotFather

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(content_types=['audio', 'voice', 'document', 'video', 'photo'])
def send_direct_url(message):
    # لو نوع الرسالة صورة (photo) بيبقى عبارة عن لست، بناخد أكبر جودة
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

    # نبني الرابط المؤقت المباشر
    direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    # نرد على المستخدم بالرابط
    bot.reply_to(message, f"✅ الرابط المباشر (صالح لفترة قصيرة):\n{direct_url}")

bot.polling()
