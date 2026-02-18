import os
import time
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
import threading
import re
import openai

# ======================
# Stage 1 — Basic Setup
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ADMIN_ID = 326193841
PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085"

FREE_AI_LIMIT = 3
SUBSCRIPTION_DAYS = 30
SUBSCRIBER_BUDGET = 6.0   # داخلي فقط
AI_COST = 0.10            # خصم داخلي

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is not set")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY is not set")

openai.api_key = OPENAI_API_KEY

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
START_TIME = time.time()

print("Zentra AI bot started")

# ======================
# Database
# ======================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined_at INTEGER,
    total_messages INTEGER DEFAULT 0,
    daily_ai INTEGER DEFAULT 0,
    last_daily_reset INTEGER,
    subscription_until INTEGER DEFAULT 0,
    budget REAL DEFAULT 0.0
)
""")
conn.commit()

# ======================
# Helpers
# ======================
def now():
    return int(time.time())

def user_exists(user_id):
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def add_user(user_id):
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, joined_at, last_daily_reset, budget)
        VALUES (?, ?, ?, ?)
    """, (user_id, now(), now(), 0.0))
    conn.commit()

def reset_daily_if_needed(user_id):
    cursor.execute("SELECT last_daily_reset FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row and now() - row[0] >= 86400:
        cursor.execute("""
            UPDATE users
            SET daily_ai = 0,
                last_daily_reset = ?
            WHERE user_id = ?
        """, (now(), user_id))
        conn.commit()

def has_active_subscription(user_id):
    cursor.execute("SELECT subscription_until FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] > now()

def activate_subscription(user_id):
    expire = now() + SUBSCRIPTION_DAYS * 86400
    cursor.execute("""
        UPDATE users
        SET subscription_until=?,
            budget=?
        WHERE user_id=?
    """, (expire, SUBSCRIBER_BUDGET, user_id))
    conn.commit()
    return expire

# ======================
# Messages
# ======================
def payment_instructions_message():
    return (
        "💳 Payment Instructions (Important)\n"
        "Send USDT via TRC20 network only.\n\n"
        "Supported platforms:\n"
        "- Binance\n- OKX\n- Bybit\n- Trust Wallet\n- MetaMask\n\n"
        "⚠️ Wrong network may cause loss of funds.\n\n"
        f"🔗 {PAYMENT_URL}\n\n"
        "----------------------------------\n"
        "💳 تعليمات الدفع (مهم)\n"
        "أرسل USDT عبر شبكة TRC20 فقط.\n\n"
        "المنصات المدعومة:\n"
        "- Binance\n- OKX\n- Bybit\n- Trust Wallet\n- MetaMask\n\n"
        "⚠️ الإرسال عبر شبكة خاطئة قد يؤدي لفقدان الأموال.\n\n"
        f"🔗 {PAYMENT_URL}"
    )

def budget_exhausted_message():
    return (
        "✨ You’ve reached your monthly AI limit.\n"
        "Thank you for using Zentra AI — you can renew anytime.\n\n"
        "✨ لقد وصلت إلى الحد الشهري لاستخدام الذكاء الاصطناعي.\n"
        "شكرًا لاستخدامك Zentra AI — يمكنك التجديد في أي وقت."
    )

def subscription_activated_message(expire):
    date = datetime.fromtimestamp(expire).strftime("%Y-%m-%d")
    return (
        "✅ Subscription activated successfully\n"
        f"📅 Valid until: {date}\n\n"
        "✅ تم تفعيل الاشتراك بنجاح\n"
        f"📅 ينتهي بتاريخ: {date}"
    )

# ======================
# OpenAI
# ======================
def call_openai(prompt):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful, clear, friendly AI assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return res.choices[0].message["content"].strip()
    except:
        return (
            "❌ AI Error\nTry again later.\n\n"
            "❌ حدث خطأ في الذكاء الاصطناعي\nحاول لاحقًا"
        )

# ======================
# Handlers
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    if not user_exists(uid):
        add_user(uid)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Zentra AI\n"
        "🤖 Just write and I’ll reply.\n\n"
        "👋 مرحبًا بك في Zentra AI\n"
        "🤖 اكتب أي شيء وسأرد\n"
        "مباشرة"
    )

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    uid = message.from_user.id
    text = message.text or ""

    if not user_exists(uid):
        add_user(uid)

    reset_daily_if_needed(uid)
    cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
    daily_used, budget = cursor.fetchone()

    if not has_active_subscription(uid):
        if daily_used >= FREE_AI_LIMIT:
            bot.send_message(message.chat.id, payment_instructions_message())
            return
    else:
        if budget <= 0:
            bot.send_message(message.chat.id, budget_exhausted_message())
            return

    cursor.execute("""
        UPDATE users
        SET daily_ai = daily_ai + 1,
            total_messages = total_messages + 1,
            budget = CASE WHEN budget > 0 THEN budget - ? ELSE budget END
        WHERE user_id=?
    """, (AI_COST, uid))
    conn.commit()

    reply = call_openai(text)
    bot.send_message(message.chat.id, reply)

# ======================
# Webhook
# ======================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data and data.get("payment_status") == "finished":
        uid = int(data.get("order_id"))
        if not user_exists(uid):
            add_user(uid)
        expire = activate_subscription(uid)
        bot.send_message(uid, subscription_activated_message(expire))
    return jsonify({"ok": True})

# ======================
# Run
# ======================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling(skip_pending=True)
