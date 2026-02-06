import os
import telebot
import time
import io
from PIL import Image
from rembg import remove

# =========================
# Environment
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

START_TIME = time.time()

# =========================
# /start
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        "👋 Welcome to Zentra AI (Beta)\n"
        "أهلاً بك في Zentra AI (نسخة تجريبية)\n\n"
        "➕ Math example / مثال حسابي:\n"
        "3+19\n\n"
        "🖼 Send an image to remove background\n"
        "📸 أرسل صورة لإزالة الخلفية\n\n"
        "⏱ Bot works 24/7"
    )

# =========================
# Math (simple addition)
# =========================
@bot.message_handler(func=lambda m: '+' in m.text)
def add_numbers(message):
    chat_id = message.chat.id
    try:
        a, b = message.text.split('+')
        result = int(a.strip()) + int(b.strip())
        bot.send_message(
            chat_id,
            f"✅ Result / النتيجة: {result}"
        )
    except:
        bot.send_message(
            chat_id,
            "❌ Invalid format / صيغة غير صحيحة\n"
            "Example / مثال: 3+19"
        )

# =========================
# Status (admin later)
# =========================
@bot.message_handler(commands=['status'])
def status(message):
    chat_id = message.chat.id
    uptime = int(time.time() - START_TIME)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    bot.send_message(
        chat_id,
        f"📊 Zentra AI Status\n"
        f"⏱ Uptime: {hours}h {minutes}m\n"
        f"✅ Bot is running normally"
    )

# =========================
# Background Removal (Transparent PNG)
# =========================
@bot.message_handler(content_types=['photo'])
def remove_background(message):
    chat_id = message.chat.id

    bot.send_message(
        chat_id,
        "🧠 Removing background...\n"
        "جاري إزالة الخلفية..."
    )

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        input_image = Image.open(io.BytesIO(downloaded)).convert("RGBA")
        output_image = remove(input_image)

        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        bot.send_photo(
            chat_id,
            output_buffer,
            caption="✅ Background removed successfully\n"
                    "✅ تم إزالة الخلفية بنجاح"
        )

    except Exception as e:
        bot.send_message(
            chat_id,
            "❌ Failed to process image\n"
            "❌ فشل معالجة الصورة"
        )

# =========================
# Run
# =========================
bot.infinity_polling()
