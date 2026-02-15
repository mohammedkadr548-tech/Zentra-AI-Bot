import os
import re
import telebot
from telebot import types

# قراءة التوكن من متغير البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in environment variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# إنشاء الأزرار تحت كل رسالة
def action_buttons(result_text):
    markup = types.InlineKeyboardMarkup(row_width=4)

    like_btn = types.InlineKeyboardButton("👍", callback_data="like")
    dislike_btn = types.InlineKeyboardButton("👎", callback_data="dislike")
    copy_btn = types.InlineKeyboardButton("📋 نسخ", callback_data=f"copy:{result_text}")
    share_btn = types.InlineKeyboardButton("🔗 مشاركة", switch_inline_query=result_text)

    markup.add(like_btn, dislike_btn, copy_btn, share_btn)
    return markup


# رسالة البداية
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 أهلاً بك\n\n"
        "🧮 أرسل عملية جمع مثل:\n"
        "<code>5+7</code>\n"
        "<code>10 + 3</code>"
    )


# التقاط عمليات الجمع فقط
@bot.message_handler(func=lambda m: True)
def calculate(message):
    text = message.text.replace(" ", "")

    # تحقق من صيغة جمع فقط
    if not re.fullmatch(r"\d+\+\d+", text):
        bot.send_message(
            message.chat.id,
            "❌ الصيغة غير صحيحة\nمثال صحيح:\n<code>6+7</code>"
        )
        return

    a, b = text.split("+")
    result = int(a) + int(b)

    result_text = f"{a} + {b} = <b>{result}</b>"

    bot.send_message(
        message.chat.id,
        result_text,
        reply_markup=action_buttons(result_text)
    )


# أزرار التفاعل
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data == "like":
        bot.answer_callback_query(call.id, "👍 شكراً على التفاعل")
    elif call.data == "dislike":
        bot.answer_callback_query(call.id, "👎 تم الاستلام")
    elif call.data.startswith("copy:"):
        bot.answer_callback_query(call.id, "📋 انسخ النتيجة يدويًا")


# تشغيل البوت (Polling فقط)
bot.infinity_polling()
