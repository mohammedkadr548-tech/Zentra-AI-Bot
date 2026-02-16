# ===============================
# Zentra AI - Final Unified Code
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

def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return cursor.fetchone()

def create_user(uid):
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, joined_at, last_reset)
        VALUES (?, ?, ?)
    """, (uid, now(), now()))
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

def subscription_active(user):
    return user[1] == 1 and user[2] > now()

def check_channel(uid):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ===============================
# 4️⃣ Messages
# ===============================
def subscribe_message(uid):
    return (
        "🚀 <b>Upgrade to Premium</b>\n"
        "Subscribe to continue using Zentra AI.\n\n"
        "🚀 <b>الترقية إلى الاشتراك المدفوع</b>\n"
        "اشترك لمتابعة استخدام Zentra AI.\n\n"
        f"🔗 {PAYMENT_URL}{uid}"
    )

def budget_exceeded():
    return (
        "⚠️ <b>Budget exhausted</b>\n"
        "Please renew your subscription.\n\n"
        "⚠️ <b>تم استهلاك الميزانية</b>\n"
        "يرجى تجديد الاشتراك."
    )

# ===============================
# 5️⃣ OpenAI
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
IMAGE_KEYWORDS = ["image", "photo", "picture", "صورة", "ارسم", "صمم"]

def is_image(text):
    t = text.lower()
    return any(k in t for k in IMAGE_KEYWORDS)

# ===============================
# 7️⃣ MAIN HANDLER (ONLY ONE)
# ===============================
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    create_user(uid)
    user = get_user(uid)
    reset_daily(user)

    # 🔒 Mandatory Channel
    if not check_channel(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(
            message,
            "🚫 Please join the channel first.\n🚫 اشترك بالقناة أولًا.",
            reply_markup=kb
        )
        return

    # 🧮 Number Addition (FREE / NO LIMIT)
    if re.match(r"^\s*\d+\s*\+\s*\d+\s*$", text):
        a, b = map(int, text.split("+"))
        bot.reply_to(message, f"✅ Result: {a+b}\n✅ النتيجة: {a+b}")
        return

    # ❌ Block admin keyword from AI
    if text.lower() == "zentra ai":
        return

    # 🔓 Free users (AI ONLY)
    if not subscription_active(user):
        if user[3] >= FREE_DAILY_LIMIT:
            bot.reply_to(message, subscribe_message(uid))
            return
        update(
            "UPDATE users SET daily_used=daily_used+1 WHERE user_id=?",
            (uid,)
        )
        bot.reply_to(
            message,
            "✅ Free AI request accepted\n"
            "✅ تم قبول طلب الذكاء الاصطناعي المجاني"
        )
        return

    # 💰 Paid user budget
    cost = IMAGE_COST if is_image(text) else TEXT_COST
    if user[5] < cost:
        bot.reply_to(message, budget_exceeded())
        return

    try:
        reply = ask_ai(text)
        update(
            "UPDATE users SET budget=budget-?, spent=spent+? WHERE user_id=?",
            (cost, cost, uid)
        )
        bot.reply_to(
            message,
            f"✅ <b>Answer:</b>\n{reply}\n\n"
            f"✅ <b>الإجابة:</b>\n{reply}"
        )
    except:
        bot.reply_to(
            message,
            "❌ AI service unavailable\n❌ خدمة الذكاء الاصطناعي غير متاحة حاليًا"
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
        bot.send_message(
            uid,
            "🎉 <b>Subscription activated</b>\n"
            "🎉 <b>تم تفعيل الاشتراك بنجاح</b>"
        )
    return jsonify({"ok": True})

# ===============================
# 9️⃣ Admin Stats
# ===============================
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "zentra ai")
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")
    paid = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(daily_used) FROM users")
    msgs = cursor.fetchone()[0] or 0

    uptime = int((time.time() - BOT_START_TIME) / 60)

    bot.reply_to(
        message,
        f"📊 <b>Zentra AI – Admin Stats</b>\n\n"
        f"👥 Total users: {total}\n"
        f"👑 Paid users: {paid}\n"
        f"💬 AI messages today: {msgs}\n"
        f"⏱ Uptime: {uptime} min\n\n"
        f"📊 <b>إحصائيات Zentra AI</b>\n\n"
        f"👥 المستخدمين: {total}\n"
        f"👑 المشتركين: {paid}\n"
        f"💬 رسائل الذكاء الاصطناعي اليوم: {msgs}\n"
        f"⏱ مدة التشغيل: {uptime} دقيقة"
    )

# ===============================
# 🔟 Run
# ===============================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling()
