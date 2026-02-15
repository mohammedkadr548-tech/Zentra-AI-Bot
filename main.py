import telebot
from telebot import types
import sqlite3
import time
import threading
from flask import Flask, request, jsonify
import hmac, hashlib

# =====================
# الإعدادات
# =====================
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN"
NOWPAYMENTS_IPN_KEY = "PUT_NOWPAYMENTS_IPN_KEY"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
START_TIME = time.time()

# =====================
# قاعدة البيانات
# =====================
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_subscribed INTEGER DEFAULT 0,
    balance REAL DEFAULT 0,
    messages_used INTEGER DEFAULT 0,
    created_at INTEGER
)
""")
conn.commit()

# =====================
# إنشاء المستخدم
# =====================
def get_user(user_id):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("""
            INSERT INTO users (user_id, created_at)
            VALUES (?,?)
        """, (user_id, int(time.time())))
        conn.commit()

# =====================
# أزرار التفاعل
# =====================
def reaction_buttons():
    kb = types.InlineKeyboardMarkup(row_width=4)
    kb.add(
        types.InlineKeyboardButton("👍", callback_data="like"),
        types.InlineKeyboardButton("👎", callback_data="dislike"),
        types.InlineKeyboardButton("📋", callback_data="copy"),
        types.InlineKeyboardButton("🔁", callback_data="share"),
    )
    return kb

# =====================
# /start
# =====================
@bot.message_handler(commands=["start"])
def start(message):
    get_user(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "🤖 مرحبًا بك في *Zentra AI*\n\n"
        "🧪 هذا وضع تجريبي\n"
        "➕ أرسل عملية جمع مثل:\n"
        "`1+1`\n\n"
        "🚀 الميزات الكاملة قريبًا",
        parse_mode="Markdown"
    )

# =====================
# جمع الأرقام (1+1)
# =====================
@bot.message_handler(func=lambda m: "+" in m.text)
def add_numbers(message):
    get_user(message.from_user.id)
    try:
        a, b = message.text.split("+")
        result = int(a.strip()) + int(b.strip())
        bot.send_message(
            message.chat.id,
            f"✅ النتيجة: {result}",
            reply_markup=reaction_buttons()
        )
    except:
        bot.send_message(
            message.chat.id,
            "❌ صيغة غير صحيحة\nمثال: 1+1",
            reply_markup=reaction_buttons()
        )

# =====================
# أزرار التفاعل
# =====================
@bot.callback_query_handler(func=lambda call: True)
def handle_reactions(call):
    if call.data == "like":
        bot.answer_callback_query(call.id, "👍 شكراً لتقييمك")
    elif call.data == "dislike":
        bot.answer_callback_query(call.id, "👎 تم تسجيل الملاحظة")
    elif call.data == "copy":
        bot.answer_callback_query(call.id, "📋 يمكنك نسخ النص يدويًا")
    elif call.data == "share":
        bot.answer_callback_query(call.id, "🔁 شارك البوت مع أصدقائك")

# =====================
# Webhook NOWPayments
# =====================
@app.route("/nowpayments", methods=["POST"])
def nowpayments_webhook():
    data = request.json
    signature = request.headers.get("x-nowpayments-sig")

    sorted_data = dict(sorted(data.items()))
    message = "&".join(f"{k}={v}" for k, v in sorted_data.items())

    generated_signature = hmac.new(
        NOWPAYMENTS_IPN_KEY.encode(),
        message.encode(),
        hashlib.sha512
    ).hexdigest()

    if generated_signature != signature:
        return jsonify({"error": "invalid signature"}), 400

    if data.get("payment_status") == "finished":
        user_id = int(data.get("order_id"))
        c.execute("""
            UPDATE users
            SET is_subscribed=1,
                balance=6
            WHERE user_id=?
        """, (user_id,))
        conn.commit()

    return jsonify({"status": "ok"})

# =====================
# تشغيل Webhook
# =====================
def run_webhook():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_webhook).start()

# =====================
# تشغيل البوت
# =====================
print("Zentra AI Bot is running...")
bot.infinity_polling()
