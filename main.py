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
ADMIN_ID = 326193841  # ⬅️ ضع ID الخاص بك (أرقام فقط)
ADMIN_SECRET = "#zentra_admin"  # كلمة المراقبة السرية

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
START_TIME = time.time()

# ======================
# رسالة البدء (بدون ذكر أي اسم)
# ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 *Zentra AI – Test Version*\n\n"
        "➕ Send math like: `3+9`\n"
        "🖼 Send an image to remove background\n"
        "⏱ Bot works 24/7\n\n"
        "👋 *Zentra AI – نسخة تجريبية*\n"
        "➕ أرسل عملية جمع مثل: `3+9`\n"
        "🖼 أرسل صورة لإزالة الخلفية\n"
        "⏱ البوت يعمل 24/7"
    )

# ======================
# جمع رقمين فقط
# ======================
@bot.message_handler(func=lambda m: m.text and '+' in m.text)
def add_numbers(message):
    try:
        a, b = message.text.split('+')
        result = int(a.strip()) + int(b.strip())
        bot.send_message(
            message.chat.id,
            f"✅ Result / النتيجة: {result}"
        )
    except:
        bot.send_message(
            message.chat.id,
            "❌ Invalid format\nExample: 3+9\n\n"
            "❌ صيغة غير صحيحة\nمثال: 3+9"
        )

# ======================
# إزالة الخلفية (PNG شفاف)
# ======================
@bot.message_handler(content_types=['photo'])
def remove_background(message):
    try:
        bot.send_message(
            message.chat.id,
            "🧠 Removing background...\n"
            "جاري إزالة الخلفية..."
        )

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

    except:
        bot.send_message(
            message.chat.id,
            "❌ Error processing image\nحدث خطأ أثناء معالجة الصورة"
        )

# ======================
# نظام المراقبة السري (بدون ظهور أي اسم)
# ======================
@bot.message_handler(func=lambda m: m.text == ADMIN_SECRET)
def admin_status(message):
    if message.from_user.id != ADMIN_ID:
        return

    # حذف رسالة الأدمن فورًا (لا اسم – لا أثر)
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    uptime = int(time.time() - START_TIME)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    status_text = (
        "📊 *Zentra AI Status*\n\n"
        "🇸🇦 الحالة:\n"
        f"⏱ مدة التشغيل: {hours} ساعة {minutes} دقيقة\n"
        "✅ البوت يعمل بشكل طبيعي\n\n"
        "🇬🇧 Status:\n"
        f"⏱ Uptime: {hours}h {minutes}m\n"
        "✅ Bot is running normally"
    )

    bot.send_message(message.chat.id, status_text)

# ======================
# تشغيل البوت
# ======================
print("Zentra AI bot is running...")
bot.infinity_polling()
