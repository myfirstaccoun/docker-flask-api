from telethon import TelegramClient, events
import telebot
import asyncio

# إعدادات Telethon
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_YT = '@BotYouTubeDownloadBot'

# إعدادات Telebot
TELEBOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"
bot = telebot.TeleBot(TELEBOT_TOKEN)

# Event loop
loop = asyncio.get_event_loop()
client = TelegramClient('session_name', API_ID, API_HASH, loop=loop)

# مثال: استقبال من BOT_YT عبر Telethon والرد عن طريق Telebot
@client.on(events.NewMessage(from_users=BOT_YT))
async def handle_yt_reply(event):
    print(f"[رد من {BOT_YT}]: {event.text}")
    # إرسال رسالة لأي يوزر/شات عبر Telebot
    bot.send_message(chat_id=123456789, text=f"البوت رد: {event.text}")

async def main():
    await client.start()
    # إرسال رسالة إلى BOT_YT
    await client.send_message(BOT_YT, "hello")

loop.run_until_complete(main())
client.run_until_disconnected()
