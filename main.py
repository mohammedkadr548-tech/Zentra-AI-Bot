# ===============================
# Zentra AI – Final Clean Version
# ===============================

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

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN not set")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY not set")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

ADMIN_ID = 326193841
BOT_START_TIME = time.time()

PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085&order_id="

SUBSCRIPTION_DAYS = 30
SUBSCRIBER_BUDGET = 6.0

FREE_DAILY_LIMIT = 3
TEXT_COST = 0.10
IMAGE_COST = 0.04

CHANNEL_USERNAME = "@ZentraAI_Official"
CHANNEL_LINK = "https://t.me/ZentraAI_Official"

# ===============================
# 2️⃣ Database (SQLite)
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
    budget REAL DEFAULT 0.0,
    spent REAL DEFAULT 0.0,
    joined_at INTEGER
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
        INSERT OR IGNORE INTO users (user_id, joined_at, last_reset)
        VALUES (?, ?, ?)
    """, (user_id, now(), now()))
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

def must_join_channel(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ===============================
# 4️⃣ Messages
# ===============================
def subscribe_message(uid):
    return (
        "🚀 Upgrade to Premium\n"
        "Subscribe to continue using Zentra AI.\n\n"
        "🚀 الترقية إلى الاشتراك المدفوع\n"
        "اشترك لمتابعة استخدام Zentra AI.\n\n"
        f"🔗 {PAYMENT_URL}{uid}"
    )

def budget_exceeded_message():
    return (
        "⚠️ Budget limit reached\n"
        "Please renew your subscription.\n\n"
        "⚠️ تم استهلاك الميزانية\n"
        "يرجى تجديد الاشتراك."
    )

# ===============================
# 5️⃣ AI
# ===============================
def ask_ai(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# ===============================
# 6️⃣ Image Detection
# ===============================
IMAGE_KEYWORDS = [
    "image", "photo", "picture", "draw", "design",
    "صورة", "ارسم", "صمم", "تصميم"
]

def is_image_request(text):
    t = text.lower()
    return any(k in t for k in IMAGE_KEYWORDS)

# ===============================
# 7️⃣ MAIN HANDLER (ONE ONLY)
# ===============================
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    user_id = message.from_user.id
    text = message.text or ""

    create_user(user_id)
    user = get_user(user_id)
    reset_daily(user)

    # ========= ADMIN COMMAND =========
    if text.lower() == "zentra ai":
        if user_id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")
        paid_users = cursor.fetchone()[0]

        uptime = int((time.time() - BOT_START_TIME) / 60)

        bot.send_message(
            message.chat.id,
            f"📊 Zentra AI – Admin Stats\n\n"
            f"👥 Total users: {total_users}\n"
            f"👑 Paid users: {paid_users}\n"
            f"⏱ Uptime: {uptime} min\n\n"
            f"📊 إحصائيات Zentra AI\n"
            f"👥 المستخدمين: {total_users}\n"
            f"👑 المشتركين: {paid_users}"
        )
        return

    # ========= NUMBER ADDITION (FREE TEST) =========
    if re.match(r"^\s*\d+\s*\+\s*\d+\s*$", text):
        a, b = map(int, text.split("+"))
        bot.send_message(
            message.chat.id,
            f"✅ Result: {a+b}\n"
            f"✅ النتيجة: {a+b}"
        )
        return

    # ========= CHANNEL CHECK =========
    if not must_join_channel(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.send_message(
            message.chat.id,
            "🚫 Please join the channel first.\n"
            "🚫 يجب الاشتراك بالقناة أولًا.",
            reply_markup=kb
        )
        return

    # ========= FREE USER =========
    if not is_subscribed(user):
        if user[3] >= FREE_DAILY_LIMIT:
            bot.send_message(message.chat.id, subscribe_message(user_id))
            return

        update(
            "UPDATE users SET daily_used=daily_used+1 WHERE user_id=?",
            (user_id,)
        )

        bot.send_message(
            message.chat.id,
            "✅ Free request accepted\n"
            "✅ تم قبول الطلب المجاني"
        )
        return

    # ========= SUBSCRIBER =========
    is_image = is_image_request(text)
    cost = IMAGE_COST if is_image else TEXT_COST

    if user[5] < cost:
        bot.send_message(message.chat.id, budget_exceeded_message())
        return

    try:
        reply = ask_ai(text)
        update(
            "UPDATE users SET budget=budget-?, spent=spent+? WHERE user_id=?",
            (cost, cost, user_id)
        )
        bot.send_message(
            message.chat.id,
            f"✅ Answer:\n{reply}\n\n"
            f"✅ الإجابة:\n{reply}"
        )
    except:
        bot.send_message(
            message.chat.id,
            "❌ AI service error\n"
            "❌ خطأ في خدمة الذكاء الاصطناعي"
        )

# ===============================
# 8️⃣ NOWPayments Webhook
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data and data.get("payment_status") == "finished":
        uid = int(data.get("order_id"))
        create_user(uid)
        update(
            "UPDATE users SET is_subscribed=1, sub_end=?, budget=? WHERE user_id=?",
            (now() + SUBSCRIPTION_DAYS * 86400, SUBSCRIBER_BUDGET, uid)
        )
        bot.send_message(uid, "🎉 Subscription activated\n🎉 تم تفعيل الاشتراك")
    return jsonify({"ok": True})

# ===============================
# 9️⃣ RUN
# ===============================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling()
