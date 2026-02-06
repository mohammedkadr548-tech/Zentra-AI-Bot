import telebot
import time
import io
import os
from PIL import Image
from rembg import remove

# ======================
# الإعدادات
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # التوكن من السيرفر فقط
ADMIN_ID = 326193841  # ⬅️ ضع ID الخاص بك هنا (أرقام فقط)

bot = telebot.TeleBot(BOT_TOKEN)
START_TIME = time.time()

# ======================
# رسالة البدء
# ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Welcome to *Zentra AI* (Test Version)\n\n"
        "➕ Send math like: `3+9`\n"
        "🖼 Send an image to remove background\n"
        "⏱ Bot works 24/7\n\n"
        "👋 مرحبًا بك في *Zentra AI* (نسخة تجريبية)\n"
        "➕ أرسل عملية جمع مثل: `3+9`\n"
        "🖼 أرسل صورة لإزالة الخلفية\n"
        "⏱ البوت يعمل 24/7",
        parse_mode="Markdown"
    )

# ======================
# جمع رقمين فقط
# ======================
@bot.message_handler(func=lambda m: m.text and '+' in m.text)
def add_numbers(message):
    try:
        a, b = message.text.split('+')
        result = int(a.strip()) + int(b.strip())
        bot.reply_to(message, f"✅ Result / النتيجة: {result}")
    except:
        bot.reply_to(
            message,
            "❌ Invalid format\n"
            "Example: 3+9\n\n"
            "❌ صيغة غير صحيحة\n"
            "مثال: 3+9"
        )

# ======================
# إزالة الخلفية (PNG شفاف)
# ======================
@bot.message_handler(content_types=['photo'])
def remove_background(message):
    msg = bot.reply_to(
        message,
        "🧠 Removing background...\n"
        "جاري إزالة الخلفية..."
    )

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        input_image = Image.open(io.BytesIO(downloaded_file)).convert("RGBA")
        output_image = remove(input_image)

        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        bot.send_document(
            message.chat.id,
            output_buffer,
            visible_file_name="zentra_ai.png",
            caption="✅ Background removed successfully\nتمت إزالة الخلفية بنجاح"
        )
    except Exception as e:
        bot.reply_to(message, "❌ Error processing image")

# ======================
# أمر المراقبة السري
# ======================
@bot.message_handler(commands=['status'])
def status(message):
    if message.from_user.id != ADMIN_ID:
        return

    uptime = int(time.time() - START_TIME)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    bot.reply_to(
        message,
        f"📊 Zentra AI Status\n"
        f"⏱ Uptime: {hours}h {minutes}m\n"
        f"✅ Bot is running normally"
    )

# ======================
# تشغيل البوت
# ======================
print("Zentra AI bot is running...")
bot.infinity_polling()
