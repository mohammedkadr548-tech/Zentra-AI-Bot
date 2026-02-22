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
# Stage 1 — ENV
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET")

if not all([BOT_TOKEN, OPENAI_API_KEY, NOWPAYMENTS_API_KEY, NOWPAYMENTS_IPN_SECRET]):
    raise RuntimeError("Missing environment variables")

openai.api_key = OPENAI_API_KEY

# ======================
# Stage 2 — CONSTANTS
# ======================
PRICE_USD = 10
SUBSCRIPTION_DAYS = 30
FREE_AI_LIMIT = 3
SUBSCRIBER_BUDGET = 6.0

NOWPAYMENTS_CREATE_PAYMENT = "https://api.nowpayments.io/v1/payment"
WEBHOOK_URL = "https://zentra-ai-bot-production.up.railway.app/webhook"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ======================
# Stage 3 — DATABASE
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
# Stage 4 — HELPERS
# ======================
def now():
    return int(time.time())

def add_user(uid):
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, joined_at, last_daily_reset, budget)
        VALUES (?, ?, ?, 0)
    """, (uid, now(), now()))
    conn.commit()

def reset_daily(uid):
    cursor.execute("SELECT last_daily_reset FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    if row and now() - row[0] >= 86400:
        cursor.execute("""
            UPDATE users SET daily_ai=0, last_daily_reset=?
            WHERE user_id=?
        """, (now(), uid))
        conn.commit()

def has_subscription(uid):
    cursor.execute("SELECT subscription_until FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    return row and row[0] > now()

def activate_subscription(uid):
    expire = now() + SUBSCRIPTION_DAYS * 86400
    cursor.execute("""
        UPDATE users SET subscription_until=?, budget=?
        WHERE user_id=?
    """, (expire, SUBSCRIBER_BUDGET, uid))
    conn.commit()

# ======================
# Stage 5 — CREATE PAYMENT API
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
        "order_description": "Zentra AI — 30 Days Subscription",
        "ipn_callback_url": WEBHOOK_URL
    }

    r = requests.post(NOWPAYMENTS_CREATE_PAYMENT, headers=headers, json=payload)
    data = r.json()
    return data.get("invoice_url")

# ======================
# Stage 6 — MESSAGES
# ======================
WELCOME_MESSAGE = (
    "👋 Welcome to Zentra AI\n"
    "🤖 Write anything and I’ll reply.\n\n"
    "👋 مرحبًا بك في Zentra AI\n"
    "🤖 اكتب أي شيء وسأرد عليك"
)

def payment_message(uid):
    url = create_payment(uid)
    return (
        "💳 Subscribe for 30 days — 10 USDT (TRC20)\n"
        f"{url}\n\n"
        "💳 اشترك لمدة 30 يوم — 10 USDT (TRC20)\n"
        f"{url}"
    )

# ======================
# Stage 7 — AI
# ======================
def call_ai_text(prompt):
    res = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700
    )
    reply = res.choices[0].message["content"]
    cost = (res.usage.total_tokens / 1000) * 0.002
    return reply, cost

# ======================
# Stage 8 — TELEGRAM
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    add_user(message.from_user.id)
    bot.send_message(message.chat.id, WELCOME_MESSAGE)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    add_user(uid)
    reset_daily(uid)

    cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
    daily, budget = cursor.fetchone()

    if not has_subscription(uid) and daily >= FREE_AI_LIMIT:
        bot.send_message(message.chat.id, payment_message(uid))
        return

    if has_subscription(uid) and budget <= 0:
        bot.send_message(message.chat.id, "✨ Monthly limit reached")
        return

    reply, cost = call_ai_text(message.text)

    cursor.execute("""
        UPDATE users
        SET daily_ai=daily_ai+1,
            budget=CASE WHEN budget>0 THEN budget-? ELSE budget END
        WHERE user_id=?
    """, (cost, uid))
    conn.commit()

    bot.send_message(message.chat.id, reply)

# ======================
# Stage 9 — NOWPayments Webhook
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
        bot.send_message(uid, "✅ Subscription activated")

    return jsonify({"ok": True})

# ======================
# Stage 10 — RUN
# ======================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask, daemon=True).start()
bot.infinity_polling(skip_pending=True)
