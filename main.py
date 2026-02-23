import os
import telebot

# ======================
# CONFIG
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ======================
# MESSAGES
# ======================
WELCOME_MESSAGE = (
    "👋 Welcome to Zentra AI\n\n"
    "⚠️ AI is temporarily offline\n"
    "🤖 Smart auto-replies are enabled\n\n"
    "👋 مرحبًا بك في Zentra AI\n"
    "⚠️ الذكاء الاصطناعي متوقف مؤقتًا\n"
    "🤖 الردود التلقائية مفعلة"
)

AUTO_REPLY = (
    "📩 وصلتني رسالتك!\n\n"
    "🤖 حاليًا الذكاء الاصطناعي قيد الإعداد\n"
    "⏳ سيتم تفعيله قريبًا جدًا\n\n"
    "💡 يمكنك المتابعة، البوت يعمل بشكل طبيعي"
)

GREETINGS = ["مرحبا", "هلا", "السلام", "hello", "hi"]

# ======================
# HANDLERS
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, WELCOME_MESSAGE)

@bot.message_handler(func=lambda m: True)
def reply_all(message):
    text = message.text.lower()

    if any(greet in text for greet in GREETINGS):
        bot.send_message(message.chat.id, "👋 أهلًا بك! كيف أقدر أساعدك؟")
    else:
        bot.send_message(message.chat.id, AUTO_REPLY)

# ======================
# RUN
# ======================
bot.infinity_polling(skip_pending=True)
