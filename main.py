import telebot
import time
import io
from PIL import Image
from rembg import remove

# =========================
# 🔑 الإعدادات
# =========================
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
8587162325:AAEvA3W-SVzmtM-ZO6VuTYeZyOo-C8_2hhuWg

bot = telebot.TeleBot(BOT_TOKEN)
START_TIME = time.time()

# =========================
# 🟢 رسالة البدء
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 مرحبًا بك في Zentra AI (نسخة تجريبية)\n\n"
        "➕ اكتب عملية جمع مثل:\n"
        "3+19\n\n"
        "🖼 أرسل صورة لإزالة الخلفية\n\n"
        "🚀 البوت يعمل 24/7"
    )

# =========================
# ➕ جمع رقمين
# =========================
@bot.message_handler(func=lambda m: m.text and '+' in m.text)
def add_numbers(message):
    try:
        a, b = message.text.split('+')
        result = int(a.strip()) + int(b.strip())
        bot.reply_to(message, f"✅ النتيجة: {result}")
    except:
        bot.reply_to(
            message,
            "❌ الصيغة غير صحيحة\n"
            "اكتبها هكذا:\n"
            "3+19"
        )

# =========================
# 📊 أمر المراقبة (لك فقط)
# =========================
@bot.message_handler(commands=['status'])
def status(message):
    if message.from_user.id != ADMIN_ID:
        return

    uptime = int(time.time() - START_TIME)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    bot.reply_to(
        message,
        f"🤖 Zentra AI Status\n"
        f"⏱ Uptime: {hours}h {minutes}m\n"
        f"✅ Bot is running normally"
    )

# =========================
# 🖼 إزالة خلفية الصور
# =========================
@bot.message_handler(content_types=['photo'])
def remove_background(message):
    msg = bot.reply_to(message, "🧠 جارٍ إزالة الخلفية...")

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        input_image = Image.open(io.BytesIO(downloaded_file))
        output_image = remove(input_image)

        bio = io.BytesIO()
        output_image.save(bio, format="PNG")
        bio.seek(0)

        bot.send_photo(
            message.chat.id,
            bio,
            caption="✅ تم إزالة الخلفية بنجاح"
        )

    except Exception as e:
        bot.edit_message_text(
            "❌ حدث خطأ أثناء معالجة الصورة",
            message.chat.id,
            msg.message_id
        )

# =========================
# 🚀 تشغيل البوت
# =========================
print("Zentra AI Bot is running...")
bot.infinity_polling()
