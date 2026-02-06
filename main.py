import telebot
import time
import os
import io
from PIL import Image
from rembg import remove

# ======================
# الإعدادات
# ======================

BOT_TOKEN = os.getenv("BOT_TOKEN")  # التوكن من السيرفر (Railway)
ADMIN_ID = 123456789  # ❗️ ضع هنا رقم Telegram ID الخاص بك

bot = telebot.TeleBot(BOT_TOKEN)
START_TIME = time.time()

# ======================
# رسالة البدء
# ======================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "🤖 *Zentra AI Bot (نسخة تجريبية)*\n\n"
        "🧮 جمع رقمين:\n"
        "مثال: `3+19`\n\n"
        "🖼️ إزالة خلفية الصور:\n"
        "أرسل صورة فقط\n\n"
        "⏱️ البوت يعمل 24/7",
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
        bot.reply_to(message, f"✅ النتيجة: {result}")
    except:
        bot.reply_to(
            message,
            "❌ صيغة غير صحيحة\n"
            "اكتب هكذا:\n"
            "3+19"
        )

# ======================
# أمر المراقبة (لك فقط)
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
        f"📊 *Zentra AI Status*\n\n"
        f"⏱️ Uptime: {hours}h {minutes}m\n"
        f"✅ Bot is running normally",
        parse_mode="Markdown"
    )

# ======================
# إزالة خلفية الصور
# ======================

@bot.message_handler(content_types=['photo'])
def remove_background(message):
    msg = bot.reply_to(message, "🧠 جاري إزالة الخلفية...")

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        input_image = Image.open(io.BytesIO(downloaded_file))
        output_image = remove(input_image)

        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        bot.send_photo(
            message.chat.id,
            output_buffer,
            caption="✅ تم إزالة الخلفية بنجاح"
        )
    except Exception as e:
        bot.reply_to(message, "❌ حدث خطأ أثناء معالجة الصورة")

# ======================
# تشغيل البوت
# ======================

print("🤖 Zentra AI Bot is running...")
bot.infinity_polling()
