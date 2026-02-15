import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
import time

BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

START_TIME = time.time()
TOTAL_MESSAGES = 0
USERS = set()

# ───────────────
# /start
# ───────────────
@bot.message_handler(commands=["start"])
def start(message):
    USERS.add(message.from_user.id)
    bot.reply_to(
        message,
        "👋 مرحبًا بك في <b>Zentra AI</b>\n\n"
        "🧪 اكتب عملية جمع للتجربة مثل:\n"
        "<code>1+1</code>"
    )

# ───────────────
# حساب جمع الأرقام
# ───────────────
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    global TOTAL_MESSAGES
    TOTAL_MESSAGES += 1
    USERS.add(message.from_user.id)

    text = message.text.replace(" ", "")

    # Regex للجمع فقط
    match = re.fullmatch(r"(\d+)\+(\d+)", text)
    if not match:
        return

    a = int(match.group(1))
    b = int(match.group(2))
    result = a + b

    reply_text = f"🧮 <b>نتيجة العملية</b>\n\n{a} + {b} = <b>{result}</b>"

    keyboard = InlineKeyboardMarkup(row_width=4)
    keyboard.add(
        InlineKeyboardButton("👍 لايك", callback_data="like"),
        InlineKeyboardButton("👎 دس لايك", callback_data="dislike"),
        InlineKeyboardButton("📋 نسخ", callback_data=f"copy:{result}"),
        InlineKeyboardButton("🔗 مشاركة", switch_inline_query=reply_text)
    )

    bot.send_message(message.chat.id, reply_text, reply_markup=keyboard)

# ───────────────
# التعامل مع الأزرار
# ───────────────
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data == "like":
        bot.answer_callback_query(call.id, "👍 شكراً على اللايك")
    elif call.data == "dislike":
        bot.answer_callback_query(call.id, "👎 تم تسجيل الملاحظة")
    elif call.data.startswith("copy:"):
        value = call.data.split(":")[1]
        bot.answer_callback_query(call.id, f"📋 انسخ النتيجة: {value}", show_alert=True)

# ───────────────
# إحصائيات البوت
# ───────────────
@bot.message_handler(commands=["stats"])
def stats(message):
    uptime = int(time.time() - START_TIME)
    bot.reply_to(
        message,
        f"📊 <b>إحصائيات Zentra AI</b>\n\n"
        f"👤 المستخدمون: {len(USERS)}\n"
        f"💬 الرسائل: {TOTAL_MESSAGES}\n"
        f"⏱ مدة التشغيل: {uptime} ثانية"
    )

print("Zentra AI Bot is running...")
bot.infinity_polling()
