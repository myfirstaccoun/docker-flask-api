from flask import Flask
import subprocess

app = Flask(__name__)

@app.route('/')
def hello_world():
    try:
        # شغّل أمر ffmpeg -version
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        output = result.stdout.split("\n")[0]  # أول سطر فيه الإصدار
    except FileNotFoundError:
        output = "ffmpeg not found"

    return f"Hello from Koyeb<br>FFmpeg status: {output}"

if __name__ == "__main__":
    app.run()
