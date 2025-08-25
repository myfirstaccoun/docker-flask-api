FROM python:3-alpine

WORKDIR /app

# تثبيت ffmpeg فقط (تشغيل)
RUN apk add --no-cache ffmpeg

# نسخ الملفات وتثبيت المتطلبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py app.py
COPY session_name.session .

# تشغيل البوت مباشرة
CMD ["python", "app.py"]
