from flask import Flask, request, jsonify
from flask_cors import CORS
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
import asyncio
import requests
import threading
import uuid
from pytube import YouTube
import time
import logging
import sys

# ===== إعدادات Telethon =====
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_YT = '@BotYouTubeDownloadBot'
BOT_FORWARD_ID = "@sending_files_bot"
files_channel = -1002765670994

# ===== إعدادات Bot API =====
BOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"
CHAT_ID = 123456789

# ===== تهيئة السجل (Logging) =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===== إعداد الجلسة =====
client = TelegramClient('session_name', API_ID, API_HASH)
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)
CORS(app)

# مخزن لكل التحميلات
downloads = {}

# حدث للإشارة إلى جاهزية Telethon
client_ready_event = threading.Event()  # <-- الإصلاح هنا

# دوال عامة
def get_video_id(link: str):
    try:
        yt = YouTube(link)
        return yt.video_id
    except Exception as e:
        logger.error(f"Error getting video ID: {e}")
        return None

async def search_messages(channel: int, keyword, yt_link, download_id, forward_to=BOT_FORWARD_ID):
    try:
        found_message = False
        async for message in client.iter_messages(channel):
            if message.text and keyword in message.text:
                found_message = True
                logger.info(f'Found message [{message.id}]: {message.text}')

                prev_id = message.id - 1
                prev_message = await client.get_messages(channel, ids=prev_id)

                if prev_message:
                    logger.info(f'Forwarding previous message [{prev_message.id}]')
                    await client.forward_messages(forward_to, prev_message)
                else:
                    logger.warning('No previous message found to forward')
                break

        if not found_message:
            logger.info(f'Starting telethon_task for {download_id}')
            asyncio.create_task(telethon_task(yt_link, download_id, keyword))
    except Exception as e:
        logger.error(f"Error in search_messages: {e}")
        downloads[download_id]["status"] = "error"

# ====== دوال Telethon ======
async def wait_for_message_with_button(bot_username, button_text, timeout=120):
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    @client.on(events.NewMessage(from_users=bot_username))
    async def handler(event):
        msg = event.message
        if msg.buttons:
            for row in msg.buttons:
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

# ====== تعديل دالة استقبال الملفات ======
@bot.message_handler(content_types=['audio', 'voice', 'document', 'video', 'photo'])
def send_direct_url(message):
    try:
        logger.info("[BOT] Received file, generating direct URL...")

        file_id = message.photo[-1].file_id if message.content_type == 'photo' else getattr(message, message.content_type).file_id

        resp = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        file_path = data["result"]["file_path"]
        direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        # البحث عن تحميل مطابق
        for dl_id, info in downloads.items():
            if info["status"] == "processing" and info["direct_url"] is None:
                downloads[dl_id]["direct_url"] = direct_url
                downloads[dl_id]["status"] = "done"
                logger.info(f"Direct URL ready for {dl_id}: {direct_url}")
                break

        bot.reply_to(message, f"✅ الرابط المباشر:\n{direct_url}")
    except Exception as e:
        logger.error(f"Error generating direct URL: {e}")
        bot.reply_to(message, "❌ حصل خطأ وأنا بجيب الرابط")

# ====== المهمة الرئيسية لـ Telethon ======
async def telethon_task(video_url, download_id, keyword):
    try:
        logger.info(f"Sending video URL to YouTube bot: {video_url}")
        await client.send_message(BOT_YT, video_url)

        logger.info("Waiting for 🔉 button...")
        event = await wait_for_message_with_button(BOT_YT, "🔉")
        if not event:
            logger.warning("Button not found")
            downloads[download_id]["status"] = "error"
            return

        msg = event.message
        clicked = False
        for r, row in enumerate(msg.buttons):
            for c, btn in enumerate(row):
                if "🔉" in btn.text.strip():
                    await msg.click(r, c)
                    logger.info(f"Clicked button: {btn.text.strip()}")
                    clicked = True
                    break
            if clicked:
                break

        logger.info("Waiting for audio message...")
        audio_event = await wait_for_audio(BOT_YT)
        if not audio_event:
            logger.warning("No audio received")
            downloads[download_id]["status"] = "error"
            return

        audio_msg = audio_event.message
        await client.forward_messages(files_channel, audio_msg)
        await client.send_message(files_channel, keyword)
        await client.forward_messages(BOT_FORWARD_ID, audio_msg)
        logger.info("Forwarded audio to direct-link bot")
    except Exception as e:
        logger.error(f"Error in telethon_task: {e}")
        downloads[download_id]["status"] = "error"

# ====== إدارة دورة حياة Telethon ======
def run_telethon():
    global client_ready_event  # <-- الإصلاح هنا
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            logger.info("Starting Telethon client...")
            with client:
                logger.info("Telethon client started successfully!")
                client_ready_event.set()
                client.run_until_disconnected()
        except Exception as e:
            logger.error(f"Telethon crashed: {e}")
            client_ready_event.clear()
            time.sleep(10)  # انتظار قبل إعادة المحاولة
            logger.info("Restarting Telethon...")

# ====== Flask Endpoints ======
@app.route("/url")
def get_url():
    if not client_ready_event.is_set():
        return jsonify({"error": "Service not ready, please try again later"}), 503

    yt_link = request.args.get("link")
    if not yt_link:
        return jsonify({"error": "No link provided"}), 400
    
    yt_id = get_video_id(yt_link)
    if not yt_id:
        return jsonify({"error": "Invalid YouTube link"}), 400

    download_id = str(uuid.uuid4())
    downloads[download_id] = {"status": "processing", "direct_url": None}

    logger.info(f"API request: {yt_link}, download_id: {download_id}")
    
    # البحث عن الرسالة
    asyncio.run_coroutine_threadsafe(
        search_messages(files_channel, yt_id, yt_link, download_id), 
        client.loop
    )

    return jsonify({"download_id": download_id, "status": "started"})

@app.route("/status")
def check_status():
    download_id = request.args.get("id")
    if not download_id or download_id not in downloads:
        return jsonify({"error": "Invalid download ID"}), 400

    return jsonify(downloads[download_id])

# ====== الصفحة الرئيسية ======
@app.route('/')
def home():
    telethon_status = "Connected" if client_ready_event.is_set() else "Disconnected"
    return f"Flask + Telebot + Telethon is running!<br>Telethon status: {telethon_status}"

# ====== بدء الخدمات ======
def start_services():
    global client_ready_event
    
    # إعادة ضبط الحدث في حالة إعادة التشغيل
    client_ready_event.clear()
    
    # بدء Telethon في thread منفصل
    telethon_thread = threading.Thread(target=run_telethon, daemon=True, name="TelethonThread")
    telethon_thread.start()
    
    # انتظار تهيئة Telethon (بحد أقصى 60 ثانية)
    if not client_ready_event.wait(timeout=60):
        logger.error("Telethon failed to start within timeout")
    
    # بدء Telebot
    bot_thread = threading.Thread(
        target=lambda: bot.infinity_polling(logger_level=logging.INFO),
        daemon=True,
        name="TelebotThread"
    )
    bot_thread.start()
    
    logger.info("All services started successfully")

# ====== تهيئة التطبيق ======
if __name__ == "__main__":
    start_services()
    app.run(host="0.0.0.0", port=8000)
else:
    # تهيئة عند التشغيل مع Gunicorn
    start_services()
