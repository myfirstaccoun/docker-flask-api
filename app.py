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

# ===== إعدادات Telethon =====
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_YT = '@BotYouTubeDownloadBot'
BOT_FORWARD_ID = "@sending_files_bot"
files_channel = -1002765670994

# ===== إعدادات Bot API (بوتك الشخصي) =====
BOT_TOKEN = "8403385790:AAEPnBveQG2TuBQuYjRwTXc3MXp5T4T0NHw"
CHAT_ID = 123456789  # ID المحادثة اللي هيجيلها الرابط

session_str = ''
client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)
CORS(app)

# مخزن لكل التحميلات: 
# كل مفتاح هو download_id، والقيمة dict فيها status و direct_url
downloads = {}

# نخزن الـ loop الخاص بـ Telethon
telethon_loop = None

# دوال عامة
def get_video_id(link: str):
    yt = YouTube(link)
    video_id = yt.video_id
    return video_id

async def search_messages(channel: int, keyword, yt_link, download_id, forward_to=BOT_FORWARD_ID):
    found_message = False
    async for message in client.iter_messages(channel):
        if message.text and keyword in message.text:
            found_message = True
            print(f'Found message [{message.id}] : {message.text}')

            # خذ الرسالة السابقة بناءً على ID
            prev_id = message.id - 1  # لأن Telethon عداد الرسائل ينزل (الأرقام تصغر مع الرسائل القديمة)
            prev_message = await client.get_messages(channel, ids=prev_id)

            if prev_message:
                print(f'Forwarding previous message [{prev_message.id}]')
                await client.forward_messages(forward_to, prev_message)
            else:
                print('No previous message found to forward')
            # لو عايز توقف عند أول نتيجة، اعمل return أو break
            break

    if found_message == False:
        future = asyncio.run_coroutine_threadsafe(telethon_task(yt_link, download_id, keyword), telethon_loop)

# ====== دوال Telethon (كما في الكود الأساسي) ======
async def wait_for_message_with_button(bot_username, button_text, timeout=120):
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    @client.on(events.NewMessage(from_users=bot_username))
    async def handler(event):
        msg = event.message
        if msg.buttons:
            total_buttons = sum(len(row) for row in msg.buttons)
            if total_buttons > 1:
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

# ====== تعديل دالة استقبال الملفات من بوت telegram.Bot ======
@bot.message_handler(content_types=['audio', 'voice', 'document', 'video', 'photo'])
def send_direct_url(message):
    print("[DEBUG] Bot received file, generating direct URL...")

    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
    else:
        file_id = getattr(message, message.content_type).file_id

    resp = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
        params={"file_id": file_id}
    )
    data = resp.json()
    if not data.get("ok"):
        bot.reply_to(message, "❌ حصل خطأ وأنا بجيب الرابط")
        return

    file_path = data["result"]["file_path"]
    direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    # احنا ما نعرفش download_id هنا مباشرة، نحتاج طريقة لربط الرابط بالتحميل الصحيح.
    # الحل: نبحث في النص عن Download ID، أو نخزن آخر تحميل مؤقتا.

    # مثال هنا نفترض آخر تحميل في downloads هو آخر عنصر مفتوح
    # (يمكن تحسينه حسب تصميمك)
    for dl_id, info in downloads.items():
        if info["status"] == "processing" and info["direct_url"] is None:
            downloads[dl_id]["direct_url"] = direct_url
            downloads[dl_id]["status"] = "done"
            print(f"[DEBUG] Direct URL ready for download_id {dl_id}: {direct_url}")
            break

    bot.reply_to(message, f"✅ الرابط المباشر:\n{direct_url}")

# ====== المهمة الرئيسية لـ Telethon ======
async def telethon_task(video_url, download_id, keyword):
    print(f"[DEBUG] Sending video URL to YouTube bot: {video_url}")
    await client.send_message(BOT_YT, video_url)

    print("[DEBUG] Waiting for 🔉 button...")
    event = await wait_for_message_with_button(BOT_YT, "🔉")
    if not event:
        print("[DEBUG] Button not found")
        downloads[download_id]["status"] = "error"
        return

    msg = event.message
    for r, row in enumerate(msg.buttons):
        for c, btn in enumerate(row):
            if "🔉" in btn.text.strip():
                asyncio.create_task(msg.click(r, c))
                print(f"[DEBUG] Clicked button at [{r},{c}] with text {btn.text.strip()}")
                break

    print("[DEBUG] Waiting for audio message...")
    audio_event = await wait_for_audio(BOT_YT)
    if not audio_event:
        print("[DEBUG] No audio received")
        downloads[download_id]["status"] = "error"
        return

    audio_msg = audio_event.message
    await client.forward_messages(files_channel, audio_msg)
    await client.send_message(files_channel, keyword)
    await client.forward_messages(BOT_FORWARD_ID, audio_msg)
    print("[DEBUG] Forwarded audio to direct-link bot")

telethon_loop = asyncio.new_event_loop()
client_ready_event = threading.Event()
is_started = False
def start_client():
    global is_started

    is_started = 1
    global telethon_loop
    print("[DEBUG] Starting Telethon client...")
    asyncio.set_event_loop(telethon_loop)

    async def runner():
        await client.start()
        print("[DEBUG] Telethon connected and authorized")
        client_ready_event.set()  # هنا بنعلم إن client جاهز

    is_started = True
    telethon_loop.run_until_complete(runner())
    telethon_loop.run_forever()

# ====== Flask Endpoints ======
@app.route("/")
def print_status():
    return jsonify({"is_started": is_started}), 200

# 1) نبدأ التحميل ونعطي download_id فوراً:
@app.route("/url")
def get_url():
    global telethon_loop
    if not client_ready_event.is_set():
        return jsonify({"error": "Service not ready, please try again later"}), 503

    if telethon_loop is None:
        return jsonify({"error": "Service not ready, please try again later"}), 503

    yt_link = request.args.get("link")
    if not yt_link:
        return jsonify({"error": "No link provided"}), 400
    yt_id = get_video_id(yt_link)

    download_id = str(uuid.uuid4())
    downloads[download_id] = {"download_id": download_id, "status": "processing", "direct_url": None}

    print(f"[DEBUG] API request received for link: {yt_link}, download_id: {download_id}")
    
    # نبحث عن الرسالة
    future_search = asyncio.run_coroutine_threadsafe(search_messages(files_channel, yt_id, yt_link, download_id), telethon_loop)
    try:
        future_search.result(timeout=15)  # ممكن تحط timeout مناسب
    except Exception as e:
        print(f"[ERROR] Searching messages failed: {e}")

    # ننفذ مهمة telethon_task داخل الـ event loop الخاص به:
    # future = asyncio.run_coroutine_threadsafe(telethon_task(yt_link, download_id), telethon_loop)

    # ما نستنى نخلص (future.result()) هنا، نرجع download_id فوراً:
    # لو تريد تنتظر، يمكن تعمل future.result() لكن مع خطر timeout.

    return jsonify({"download_id": download_id, "status": "started"})

# 2) نتحقق من حالة التحميل:
@app.route("/status")
def check_status():
    download_id = request.args.get("id")
    if not download_id or download_id not in downloads:
        return jsonify({"error": "Invalid download ID"}), 400

    return jsonify(downloads[download_id])

# ====== Main ======
if __name__ == "__main__":
    threading.Thread(target=start_client, daemon=True).start()

    # # انتظر حتى client يبدأ
    # client_ready_event.wait()

    threading.Thread(target=lambda: bot.polling(non_stop=True), daemon=True).start()
    app.run(host="0.0.0.0", port=8000)
