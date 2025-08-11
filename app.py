from flask import Flask, request, jsonify
from flask_cors import CORS
from telethon import TelegramClient, events
import telebot
from telebot import types
import asyncio
import requests
import threading
import uuid
from pytube import YouTube
import time

# ===== إعدادات Telethon =====
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_YT = '@BotYouTubeDownloadBot'
BOT_FORWARD_ID = "@sending_files_bot"
files_channel = -1002765670994

# ===== إعدادات Bot API (بوتك الشخصي) =====
BOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"
CHAT_ID = 123456789  # ID المحادثة اللي هيجيلها الرابط

client = TelegramClient('session_name', API_ID, API_HASH)
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)
CORS(app)

downloads = {}
telethon_loop = None
loop_ready = threading.Event()

# رابط الويب هوك على Koyeb
WEBHOOK_URL = "https://mysterious-sapphira-yuag-7830d5f3.koyeb.app/webhook"

# ===== إعداد الويب هوك =====
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

# ===== دوال عامة =====
def get_video_id(link: str):
    yt = YouTube(link)
    return yt.video_id

async def search_messages(channel: int, keyword, yt_link, download_id, forward_to=BOT_FORWARD_ID):
    global telethon_loop

    found_message = False
    async for message in client.iter_messages(channel):
        if keyword in message.text:
            found_message = True
            prev_id = message.id - 1
            prev_message = await client.get_messages(channel, ids=prev_id)
            if prev_message:
                await client.forward_messages(forward_to, prev_message)
            break
    if not found_message:
        asyncio.run_coroutine_threadsafe(telethon_task(yt_link, download_id, keyword), telethon_loop)

async def wait_for_message_with_button(bot_username, button_text, timeout=120):
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    @client.on(events.NewMessage(from_users=bot_username))
    async def handler(event):
        if event.message.buttons:
            for row in event.message.buttons:
                for btn in row:
                    if button_text in btn.text.strip():
                        if not future.done():
                            future.set_result(event)
                            return

    try:
        return await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        client.remove_event_handler(handler)

async def wait_for_audio(bot_username, timeout=180):
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    @client.on(events.NewMessage(from_users=bot_username))
    async def handler(event):
        msg = event.message
        if msg.audio or msg.voice or (msg.document and msg.document.mime_type.startswith("audio/")):
            if not future.done():
                future.set_result(event)

    try:
        return await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        client.remove_event_handler(handler)

# ===== Handlers للبوت =====
@bot.message_handler(content_types=['audio', 'voice', 'document', 'video', 'photo'])
def send_direct_url(message):
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
    else:
        file_id = getattr(message, message.content_type).file_id

    resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id})
    data = resp.json()
    if not data.get("ok"):
        bot.reply_to(message, "❌ حصل خطأ وأنا بجيب الرابط")
        return

    file_path = data["result"]["file_path"]
    direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    for dl_id, info in downloads.items():
        if info["status"] == "processing" and info["direct_url"] is None:
            downloads[dl_id]["direct_url"] = direct_url
            downloads[dl_id]["status"] = "done"
            break

    bot.reply_to(message, f"✅ الرابط المباشر:\n{direct_url}")

async def telethon_task(video_url, download_id, keyword):
    await client.send_message(BOT_YT, video_url)
    event = await wait_for_message_with_button(BOT_YT, "🔉")
    if not event:
        downloads[download_id]["status"] = "error"
        return

    msg = event.message
    for r, row in enumerate(msg.buttons):
        for c, btn in enumerate(row):
            if "🔉" in btn.text.strip():
                asyncio.create_task(msg.click(r, c))
                break

    audio_event = await wait_for_audio(BOT_YT)
    if not audio_event:
        downloads[download_id]["status"] = "error"
        return

    audio_msg = audio_event.message
    await client.forward_messages(files_channel, audio_msg)
    await client.send_message(files_channel, keyword)
    await client.forward_messages(BOT_FORWARD_ID, audio_msg)

# ===== تشغيل Telethon في Thread =====
def start_client():
    global telethon_loop
    telethon_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telethon_loop)

    async def runner():
        await client.start()

    loop_ready.set()  # هنا نعلم أن telethon_loop جاهز

    telethon_loop.run_until_complete(runner())
    telethon_loop.run_forever()

# ===== Flask Endpoints =====
@app.route("/url")
def get_url():
    global telethon_loop
    if telethon_loop is None:
        return jsonify({"error": "Service not ready, please try again later."}), 503

    yt_link = request.args.get("link")
    if not yt_link:
        return jsonify({"error": "No link provided"}), 400
    yt_id = get_video_id(yt_link)

    download_id = str(uuid.uuid4())
    downloads[download_id] = {"status": "processing", "direct_url": None}

    future_search = asyncio.run_coroutine_threadsafe(search_messages(files_channel, yt_id, yt_link, download_id), telethon_loop)
    try:
        future_search.result(timeout=15)
    except Exception as e:
        print(f"[ERROR] Searching messages failed: {e}")

    return jsonify({"download_id": download_id, "status": "started"})

@app.route("/status")
def check_status():
    download_id = request.args.get("id")
    if not download_id or download_id not in downloads:
        return jsonify({"error": "Invalid download ID"}), 400
    return jsonify(downloads[download_id])

# ===== مسار الويب هوك للبوت =====
@app.route("/webhook", methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'ok', 200

# ===== Main =====
if __name__ == "__main__":
    threading.Thread(target=start_client, daemon=True).start()
    loop_ready.wait()  # ننتظر حتى تتأكد أن telethon_loop جاهز
    app.run(host="0.0.0.0", port=5000)
