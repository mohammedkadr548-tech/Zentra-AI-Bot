# ===============================
# Zentra AI — FINAL CLEAN VERSION
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

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

BOT_START_TIME = time.time()
ADMIN_ID = 326193841

# ===============================
# 2️⃣ Settings
# ===============================
PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085&order_id="
SUBSCRIPTION_DAYS = 30
SUBSCRIBER_BUDGET = 6.0

FREE_DAILY_LIMIT = 3
TEXT_COST = 0.10
IMAGE_COST = 0.04

CHANNEL_USERNAME = "@ZentraAI_Official"
CHANNEL_LINK = "https://t.me/ZentraAI_Official"

IMAGE_KEYWORDS = [
    "image", "photo", "picture", "draw", "design",
    "صورة", "ارسم", "صمم", "تصميم"
]

# ===============================
# 3️⃣ Database (SQLite)
# ===============================
conn = sqlite3.connect("zentra_ai.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_subscribed INTEGER DEFAULT 0,
    sub_end INTEGER DEFAULT 0,
    daily_messages INTEGER DEFAULT 0,
    last_daily_reset INTEGER DEFAULT 0,
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
        INSERT OR IGNORE INTO users
        (user_id, joined_at, last_daily_reset)
        VALUES (?, ?, ?)
    """, (user_id, now(), now()))
    conn.commit()

def update_user(query, params):
    cursor.execute(query, params)
    conn.commit()

# ===============================
# 4️⃣ Helpers
# ===============================
def reset_daily_if_needed(user):
    if now() - user[4] >= 86400:
        update_user(
            "UPDATE users SET daily_messages=0, last_daily_reset=? WHERE user_id=?",
            (now(), user[0])
        )

def subscription_active(user):
    return user[1] == 1 and user[2] > now()

def mandatory_channel(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def is_image_request(text):
    text = text.lower()
    return any(k in text for k in IMAGE_KEYWORDS)

# ===============================
# 5️⃣ Messages
# ===============================
def subscribe_message(user_id):
    return (
        "🚀 <b>Upgrade to Premium</b>\n"
        "You have used all free AI messages.\n\n"
        "🚀 <b>الترقية إلى الاشتراك المدفوع</b>\n"
        "لقد استهلكت جميع الرسائل المجانية.\n\n"
        f"🔗 {PAYMENT_URL}{user_id}"
    )

def budget_exceeded_message():
    return (
        "⚠️ <b>Monthly limit reached</b>\n"
        "Please renew your subscription.\n\n"
        "⚠️ <b>تم استهلاك الميزانية</b>\n"
        "يرجى تجديد الاشتراك."
    )

# ===============================
# 6️⃣ OpenAI Text
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
        ],
        "temperature": 0.7
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    return r.json()["choices"][0]["message"]["content"]

# ===============================
# 7️⃣ MAIN HANDLER (ONLY ONE)
# ===============================
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    user_id = message.from_user.id
    text = message.text or ""

    create_user(user_id)
    user = get_user(user_id)
    reset_daily_if_needed(user)

    # 🔒 Mandatory channel
    if not mandatory_channel(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(
            message,
            "🚫 Join the official channel first.\n"
            "🚫 اشترك في القناة الرسمية أولًا.",
            reply_markup=kb
        )
        return

    # 🧮 Number addition (FREE TEST)
    if re.match(r"^\s*\d+\s*\+\s*\d+\s*$", text):
        a, b = map(int, text.split("+"))
        bot.reply_to(
            message,
            f"✅ Result: {a+b}\n"
            f"✅ النتيجة: {a+b}"
        )
        return

    # 🆓 Free users
    if not subscription_active(user):
        if user[3] >= FREE_DAILY_LIMIT:
            bot.reply_to(message, subscribe_message(user_id))
            return

        update_user(
            "UPDATE users SET daily_messages=daily_messages+1 WHERE user_id=?",
            (user_id,)
        )

        try:
            reply = ask_ai(text)
            bot.reply_to(
                message,
                f"✅ Answer:\n{reply}\n\n"
                f"✅ الإجابة:\n{reply}"
            )
        except:
            bot.reply_to(
                message,
                "❌ AI error\n❌ خطأ في الذكاء الاصطناعي"
            )
        return

    # 💎 Subscribers only
    cost = IMAGE_COST if is_image_request(text) else TEXT_COST

    if user[5] < cost:
        bot.reply_to(message, budget_exceeded_message())
        return

    try:
        reply = ask_ai(text)
        update_user(
            "UPDATE users SET budget=budget-?, spent=spent+? WHERE user_id=?",
            (cost, cost, user_id)
        )
        bot.reply_to(
            message,
            f"✅ Answer:\n{reply}\n\n"
            f"✅ الإجابة:\n{reply}"
        )
    except:
        bot.reply_to(
            message,
            "❌ AI error\n❌ خطأ في الذكاء الاصطناعي"
        )

# ===============================
# 8️⃣ NOWPayments Webhook
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data and data.get("payment_status") == "finished":
        user_id = int(data.get("order_id"))
        create_user(user_id)
        update_user(
            "UPDATE users SET is_subscribed=1, sub_end=?, budget=? WHERE user_id=?",
            (now() + SUBSCRIPTION_DAYS * 86400, SUBSCRIBER_BUDGET, user_id)
        )
        bot.send_message(
            user_id,
            "🎉 Subscription activated\n"
            "🎉 تم تفعيل الاشتراك بنجاح"
        )
    return jsonify({"status": "ok"})

# ===============================
# 9️⃣ Admin Stats
# ===============================
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "zentra ai")
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")
    paid_users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(daily_messages) FROM users")
    daily_msgs = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(spent) FROM users")
    total_spent = cursor.fetchone()[0] or 0.0

    uptime = int((time.time() - BOT_START_TIME) / 60)

    bot.reply_to(
        message,
        f"📊 Zentra AI – Admin Stats\n\n"
        f"👥 Total users: {total_users}\n"
        f"👑 Paid users: {paid_users}\n"
        f"💬 AI messages today: {daily_msgs}\n"
        f"💰 Total AI cost: ${total_spent:.2f}\n"
        f"⏱ Uptime: {uptime} min\n\n"
        f"— — —\n"
        f"📊 إحصائيات Zentra AI\n\n"
        f"👥 المستخدمين: {total_users}\n"
        f"👑 المشتركين: {paid_users}\n"
        f"💬 رسائل اليوم: {daily_msgs}\n"
        f"💰 إجمالي المصروف: ${total_spent:.2f}"
    )

# ===============================
# 🔟 Run
# ===============================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling()
