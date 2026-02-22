import os
import time
import json
import hmac
import hashlib
import sqlite3
import threading
import requests
from flask import Flask, request, jsonify
import telebot
import openai

# ======================
# ENV
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET")

if not all([BOT_TOKEN, OPENAI_API_KEY, NOWPAYMENTS_API_KEY, NOWPAYMENTS_IPN_SECRET]):
    raise RuntimeError("Missing ENV variables")

openai.api_key = OPENAI_API_KEY

# ======================
# CONSTANTS
# ======================
FREE_AI_LIMIT = 3
PRICE_USD = 10
SUBSCRIPTION_DAYS = 30
SUBSCRIBER_BUDGET = 6.0

NOWPAYMENTS_CREATE_PAYMENT = "https://api.nowpayments.io/v1/payment"

# ⚠️ هذا فقط لـ NOWPayments IPN (ليس تيليجرام)
WEBHOOK_URL = "https://zentra-ai-bot-production.up.railway.app/webhook"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# ======================
# DATABASE
# ======================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined_at INTEGER,
    daily_ai INTEGER DEFAULT 0,
    last_daily_reset INTEGER,
    subscription_until INTEGER DEFAULT 0,
    budget REAL DEFAULT 0.0
)
""")
conn.commit()

# ======================
# HELPERS
# ======================
def now():
    return int(time.time())

def add_user(uid):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, joined_at, last_daily_reset) VALUES (?, ?, ?)",
        (uid, now(), now())
    )
    conn.commit()

def reset_daily(uid):
    cursor.execute("SELECT last_daily_reset FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    if row and now() - row[0] >= 86400:
        cursor.execute(
            "UPDATE users SET daily_ai=0, last_daily_reset=? WHERE user_id=?",
            (now(), uid)
        )
        conn.commit()

def has_subscription(uid):
    cursor.execute("SELECT subscription_until FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    return bool(row and row[0] > now())

def activate_subscription(uid):
    expire = now() + SUBSCRIPTION_DAYS * 86400
    cursor.execute(
        "UPDATE users SET subscription_until=?, budget=? WHERE user_id=?",
        (expire, SUBSCRIBER_BUDGET, uid)
    )
    conn.commit()

# ======================
# CREATE PAYMENT (API)
# ======================
def create_payment(uid):
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "price_amount": PRICE_USD,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",
        "order_id": str(uid),
        "order_description": "Zentra AI - 30 days subscription",
        "ipn_callback_url": WEBHOOK_URL
    }

    r = requests.post(NOWPAYMENTS_CREATE_PAYMENT, headers=headers, json=payload, timeout=15)
    data = r.json()
    return data.get("invoice_url")

# ======================
# AI
# ======================
def call_ai(prompt):
    res = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600
    )
    reply = res.choices[0].message["content"]
    cost = (res.usage.total_tokens / 1000) * 0.002
    return reply, cost

# ======================
# TELEGRAM
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    add_user(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "👋 Welcome to Zentra AI\n"
        "✍️ You have 3 free messages\n\n"
        "👋 مرحبًا بك في Zentra AI\n"
        "✍️ لديك 3 رسائل مجانية"
    )

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    add_user(uid)
    reset_daily(uid)

    cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
    daily, budget = cursor.fetchone()

    if not has_subscription(uid) and daily >= FREE_AI_LIMIT:
        url = create_payment(uid)
        bot.send_message(
            message.chat.id,
            f"💳 Subscribe 30 days — 10 USDT\n{url}\n\n"
            f"💳 اشترك 30 يوم — 10 USDT\n{url}"
        )
        return

    if has_subscription(uid) and budget <= 0:
        bot.send_message(message.chat.id, "✨ Monthly limit reached")
        return

    reply, cost = call_ai(message.text)

    cursor.execute(
        "UPDATE users SET daily_ai=daily_ai+1, budget=budget-? WHERE user_id=?",
        (cost if has_subscription(uid) else 0, uid)
    )
    conn.commit()

    bot.send_message(message.chat.id, reply)

# ======================
# NOWPAYMENTS WEBHOOK
# ======================
@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.data
    sig = request.headers.get("x-nowpayments-sig")

    expected = hmac.new(
        NOWPAYMENTS_IPN_SECRET.encode(),
        raw,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(expected, sig or ""):
        return jsonify({"ok": False}), 403

    data = json.loads(raw)

    if data.get("payment_status") == "finished":
        uid = int(data["order_id"])
        add_user(uid)
        activate_subscription(uid)
        bot.send_message(uid, "✅ Subscription activated\n✅ تم تفعيل الاشتراك")

    return jsonify({"ok": True})

# ======================
# RUN
# ======================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask, daemon=True).start()

# ⚠️ Polling واحد فقط
bot.infinity_polling(skip_pending=True, timeout=20)
