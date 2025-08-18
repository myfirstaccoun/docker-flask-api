import os
import uuid
import threading
import asyncio
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeAudio

app = Flask(__name__)
CORS(app)

# ===== إعدادات Telethon =====
API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
SESSION_FILE = 'session_name.session'
DOWNLOADS_DIR = 'downloads'
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Status tracking dictionary
download_status = {}

def parse_link(link):
    """Parse Telegram link into channel and message ID"""
    link = link.replace("t.me/", "").split("/")
    if len(link) < 2:
        raise ValueError("Invalid link format")
    channel = link[0]
    try:
        message_id = int(link[-1])
    except ValueError:
        raise ValueError("Message ID must be an integer")
    return channel, message_id

async def async_download_media(channel, message_id, download_id):
    """Asynchronous download function"""
    try:
        async with TelegramClient(SESSION_FILE, API_ID, API_HASH) as client:
            message = await client.get_messages(channel, ids=message_id)
            if not message or not message.media:
                download_status[download_id] = {'status': 'error', 'message': 'Media not found'}
                return

            # Find audio document
            audio_doc = None
            if hasattr(message, 'document') and message.document:
                for attr in message.document.attributes:
                    if isinstance(attr, DocumentAttributeAudio):
                        audio_doc = message.document
                        break

            if not audio_doc:
                download_status[download_id] = {'status': 'error', 'message': 'No audio found'}
                return

            filename = f"{download_id}.m4a"
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            await client.download_media(audio_doc, file_path)
            download_status[download_id] = {
                'status': 'done',
                'file_path': file_path,
                'filename': filename
            }
    except Exception as e:
        download_status[download_id] = {'status': 'error', 'message': str(e)}

def download_task(channel, message_id, download_id):
    """Run the async download in a new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_download_media(channel, message_id, download_id))
    loop.close()

@app.route('/download', methods=['GET'])
def download_audio():
    link = request.args.get('link')
    if not link:
        return jsonify({'error': 'Missing link parameter'}), 400
    
    try:
        channel, message_id = parse_link(link)
        download_id = str(uuid.uuid4())
        
        # Start download in background thread
        download_status[download_id] = {'status': 'processing'}
        threading.Thread(
            target=download_task,
            args=(channel, message_id, download_id),
            daemon=True
        ).start()
        
        return jsonify({
            'download_id': download_id,
            'status': 'processing'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/status/<download_id>', methods=['GET'])
def check_status(download_id):
    status = download_status.get(download_id, {'status': 'unknown'})
    return jsonify(status)

@app.route('/download/<filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(threaded=True, port=5000)
