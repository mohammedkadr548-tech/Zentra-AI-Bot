import os
import telebot

# ======================
# CONFIG
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ======================
# SMART REPLIES
# ======================
def smart_reply(text: str) -> str:
    t = text.lower()

    # برمجة
    if any(word in t for word in ["برمجة", "كود", "بايثون", "python", "html", "css", "api"]):
        return (
            "💻 يبدو أنك تسأل عن البرمجة\n\n"
            "ابدأ بلغة Python لأنها سهلة وقوية،\n"
            "وسنفعّل الشرح الذكي قريبًا 🤖\n\n"
            "💻 Programming question detected\n"
            "Smart AI replies coming soon 🚀"
        )

    # تقنية
    if any(word in t for word in ["تقنية", "هاتف", "اندرويد", "iphone", "انترنت", "vpn"]):
        return (
            "📱 سؤالك تقني\n\n"
            "تابع التحديثات، سيتم توفير شرح ذكي قريبًا\n\n"
            "📱 Tech question detected\n"
            "AI-powered answers coming soon"
        )

    # دين
    if any(word in t for word in ["دين", "اسلام", "صلاة", "قرآن", "الله"]):
        return (
            "📿 سؤالك ديني\n\n"
            "قال رسول الله ﷺ: «الدين النصيحة»\n"
            "وسنضيف مصادر موثوقة قريبًا\n\n"
            "📿 Religious question detected"
        )

    # كيف / ما هو
    if any(word in t for word in ["كيف", "ما هو", "شرح", "تعلم", "what", "how"]):
        return (
            "❓ سؤال ممتاز\n\n"
            "حاليًا أقدّم ردود عامة،\n"
            "وسيتم تفعيل الذكاء الاصطناعي قريبًا 🤖\n\n"
            "❓ Good question\n"
            "Full AI answers coming soon"
        )

    # رد عام
    return (
        "👋 مرحبًا بك في Zentra AI\n\n"
        "حاليًا أعمل بوضع تجريبي 🤍\n"
        "وسنفعّل الذكاء الاصطناعي قريبًا\n\n"
        "👋 Welcome to Zentra AI\n"
        "Smart AI coming very soon 🚀"
    )

# ======================
# HANDLERS
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to Zentra AI\n"
        "🤖 Smart replies are active\n\n"
        "👋 مرحبًا بك في Zentra AI\n"
        "🤖 الردود الذكية مفعلة"
    )

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    reply = smart_reply(message.text or "")
    bot.send_message(message.chat.id, reply)

# ======================
# RUN
# ======================
print("Zentra AI (Smart Mode) is running...")
bot.infinity_polling(skip_pending=True)
