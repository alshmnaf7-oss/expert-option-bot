FROM python:3.12-slim

WORKDIR /app

# نسخ وتثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع
COPY . .

# ضبط المنفذ المتوافق مع Hugging Face Spaces
ENV PORT=7860
EXPOSE 7860

# تشغيل البوت
CMD ["python", "bot.py"]
