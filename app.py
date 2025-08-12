from telethon.sessions import StringSession
from telethon import TelegramClient
from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio

API_ID = 29224979
API_HASH = 'c43959fea9767802e111a4c6cf3b16ec'
BOT_YT = '@BotYouTubeDownloadBot'

app = Flask(__name__)
CORS(app)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

session_str = ''
client = TelegramClient(StringSession(session_str), API_ID, API_HASH, loop=loop)

# فقط شغل start() بشكل عادي
client.start()

@app.route('/', methods=['GET'])
def send_message():
    message = request.args.get('message', 'Hello from Flask+Telethon via GET!')

    async def send():
        await client.send_message(BOT_YT, message)

    loop.run_until_complete(send())

    return jsonify({'status': 'message sent', 'to': BOT_YT, 'message': message})

if __name__ == '__main__':
    app.run(debug=True)
