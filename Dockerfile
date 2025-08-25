FROM python:3-alpine

WORKDIR /app

# تثبيت ffmpeg + الأدوات اللي ممكن تحتاجها المكتبات
# RUN apk add --no-cache ffmpeg gcc musl-dev libffi-dev openssl-dev

# نسخ ملفات المتطلبات
COPY requirements.txt .

# تثبيت المتطلبات (لازم يكون فيها flask + pyTelegramBotAPI)
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY app.py .
COPY session_name.session .  # لو فعلاً البوت محتاج الجلسة دي

# فتح البورت الافتراضي
EXPOSE 10000

# تشغيل البوت + السيرفر
CMD ["python", "app.py"]
