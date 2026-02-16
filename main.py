import os
import re
import time
import sqlite3
import threading
import requests
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ===============================
# 1️⃣ Basic Setup
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085&order_id="
SUBSCRIPTION_DAYS = 30
FREE_DAILY_LIMIT = 3

TEXT_COST = 0.10
IMAGE_COST = 0.40   # تكلفة الصورة (أعلى من النص)
SUBSCRIBER_BUDGET = 6.0

# ===============================
# 2️⃣ Database
# ===============================
conn = sqlite3.connect("zentra_ai.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_subscribed INTEGER DEFAULT 0,
    sub_end INTEGER DEFAULT 0,
    daily_used INTEGER DEFAULT 0,
    last_reset INTEGER DEFAULT 0,
    budget REAL DEFAULT 0.0
)
""")
conn.commit()

def now():
    return int(time.time())

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def create_user(user_id):
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, last_reset)
        VALUES (?, ?)
    """, (user_id, now()))
    conn.commit()

def update(query, params):
    cursor.execute(query, params)
    conn.commit()

# ===============================
# 3️⃣ Helpers
# ===============================
def reset_daily(user):
    if now() - user[4] >= 86400:
        update(
            "UPDATE users SET daily_used=0, last_reset=? WHERE user_id=?",
            (now(), user[0])
        )

def is_subscribed(user):
    return user[1] == 1 and user[2] > now()

def subscribe_message(uid):
    return (
        "🚀 Upgrade to Premium\n"
        "Subscribe to continue using Zentra AI.\n\n"
        "🚀 الترقية للاشتراك المدفوع\n"
        "اشترك لمتابعة استخدام Zentra AI.\n\n"
        f"🔗 {PAYMENT_URL}{uid}"
    )

def budget_message():
    return (
        "⚠️ Budget exhausted\n"
        "Please renew your subscription.\n\n"
        "⚠️ تم استهلاك الميزانية\n"
        "يرجى تجديد الاشتراك."
    )

# ===============================
# 4️⃣ AI Text
# ===============================
def ask_ai(prompt):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ]
        },
        timeout=60
    )
    return r.json()["choices"][0]["message"]["content"]

# ===============================
# 5️⃣ Image Detection
# ===============================
IMAGE_WORDS = ["image", "photo", "picture", "صورة", "ارسم", "صمم"]

def is_image_request(text):
    return any(w in text.lower() for w in IMAGE_WORDS)

# ===============================
# 6️⃣ Main Handler
# ===============================
@bot.message_handler(func=lambda m: True)
def handle(message):
    uid = message.from_user.id
    text = message.text or ""

    create_user(uid)
    user = get_user(uid)
    reset_daily(user)

    # 🧪 Number Test
    if re.match(r"^\s*\d+\s*\+\s*\d+\s*$", text):
        a, b = map(int, text.split("+"))
        bot.reply_to(message, f"✅ Result: {a+b}\n✅ النتيجة: {a+b}")
        return

    # 🔓 Free user
    if not is_subscribed(user):
        if user[3] >= FREE_DAILY_LIMIT:
            bot.reply_to(message, subscribe_message(uid))
            return

        update(
            "UPDATE users SET daily_used=daily_used+1 WHERE user_id=?",
            (uid,)
        )
        bot.reply_to(message, "✅ Free request accepted\n✅ تم قبول الطلب المجاني")
        return

    # 👑 Subscriber
    cost = IMAGE_COST if is_image_request(text) else TEXT_COST
    if user[5] < cost:
        bot.reply_to(message, budget_message())
        return

    try:
        answer = ask_ai(text)
        update(
            "UPDATE users SET budget=budget-? WHERE user_id=?",
            (cost, uid)
        )
        bot.reply_to(message, f"✅ Answer:\n{answer}\n\n✅ الإجابة:\n{answer}")
    except:
        bot.reply_to(message, "❌ AI error\n❌ خطأ في الذكاء الاصطناعي")

# ===============================
# 7️⃣ Webhook (NOWPayments)
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data and data.get("payment_status") == "finished":
        uid = int(data["order_id"])
        create_user(uid)
        update(
            "UPDATE users SET is_subscribed=1, sub_end=?, budget=? WHERE user_id=?",
            (now()+SUBSCRIPTION_DAYS*86400, SUBSCRIBER_BUDGET, uid)
        )
        bot.send_message(uid, "🎉 Subscription activated\n🎉 تم تفعيل الاشتراك")
    return jsonify({"ok": True})

# ===============================
# 8️⃣ Run
# ===============================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling()
