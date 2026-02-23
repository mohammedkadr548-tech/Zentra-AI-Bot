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
# SMART REPLY ENGINE
# ======================
def smart_reply(text: str) -> str:
    t = text.lower()

    if any(w in t for w in ["برمجة", "كود", "python", "بايثون", "api", "html"]):
        return (
            "💻 سؤال برمجة تم استقباله\n\n"
            "ابدأ بتعلم Python لأنها الأسهل والأقوى\n"
            "وسيتم تفعيل الذكاء الاصطناعي قريبًا 🤖\n\n"
            "💻 Programming mode active"
        )

    if any(w in t for w in ["كيف", "ما هو", "شرح", "تعلم", "how", "what"]):
        return (
            "❓ سؤال ممتاز\n\n"
            "حاليًا أعمل بوضع تجريبي ذكي\n"
            "وسيتم تفعيل الرد بالذكاء الاصطناعي قريبًا 🚀\n\n"
            "❓ Smart reply active"
        )

    if any(w in t for w in ["دين", "اسلام", "صلاة", "الله", "قرآن"]):
        return (
            "📿 سؤال ديني\n\n"
            "الدين النصيحة 🤍\n"
            "وسيتم إضافة مصادر موثوقة لاحقًا\n\n"
            "📿 Religious mode active"
        )

    if any(w in t for w in ["vpn", "هاتف", "اندرويد", "iphone", "تقنية"]):
        return (
            "📱 سؤال تقني\n\n"
            "تابع التحديثات، سيتم تفعيل الشرح الذكي قريبًا\n\n"
            "📱 Tech mode active"
        )

    return (
        "👋 مرحبًا بك في Zentra AI\n\n"
        "حاليًا أعمل بوضع تجريبي ذكي 🤍\n"
        "وسيتم تفعيل الذكاء الاصطناعي قريبًا جدًا\n\n"
        "👋 Welcome to Zentra AI"
    )

# ======================
# HANDLERS
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to Zentra AI\n"
        "🤖 Smart mode is active\n\n"
        "👋 مرحبًا بك في Zentra AI\n"
        "🤖 الوضع الذكي التجريبي مفعّل"
    )

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    reply = smart_reply(message.text or "")
    bot.send_message(message.chat.id, reply)

# ======================
# RUN
# ======================
print("Zentra AI is running (Smart Mode)...")
bot.infinity_polling(skip_pending=True)
