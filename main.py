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
    raise RuntimeError("Missing environment variables")

openai.api_key = OPENAI_API_KEY

# ======================
# CONSTANTS
# ======================
SUB_PRICE = 10  # USDT
SUBSCRIPTION_DAYS = 30
FREE_AI_LIMIT = 3
SUBSCRIBER_BUDGET = 6.0

# ======================
# BOT & APP
# ======================
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ======================
# DATABASE
# ======================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    daily_ai INTEGER DEFAULT 0,
    last_reset INTEGER,
    subscription_until INTEGER DEFAULT 0,
    budget REAL DEFAULT 0
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
        "INSERT OR IGNORE INTO users (user_id, last_reset) VALUES (?, ?)",
        (uid, now())
    )
    conn.commit()

def has_subscription(uid):
    cursor.execute("SELECT subscription_until FROM users WHERE user_id=?", (uid,))
    r = cursor.fetchone()
    return r and r[0] > now()

def activate_subscription(uid):
    cursor.execute("""
        UPDATE users SET
        subscription_until=?,
        budget=?
        WHERE user_id=?
    """, (now() + SUBSCRIPTION_DAYS * 86400, SUBSCRIBER_BUDGET, uid))
    conn.commit()

# ======================
# CREATE PAYMENT (API)
# ======================
def create_payment(uid):
    url = "https://api.nowpayments.io/v1/payment"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "price_amount": SUB_PRICE,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",
        "order_id": str(uid),
        "order_description": "Zentra AI - 30 days subscription",
        "ipn_callback_url": "https://zentra-ai-bot-production.up.railway.app/webhook"
    }

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["invoice_url"]

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
# HANDLERS
# ======================
@bot.message_handler(commands=["start"])
def start(m):
    add_user(m.from_user.id)
    bot.send_message(
        m.chat.id,
        "👋 Welcome to Zentra AI\n"
        "🆓 3 free messages\n"
        "💳 Subscription: 10 USDT / 30 days"
    )

@bot.message_handler(func=lambda m: True)
def chat(m):
    uid = m.from_user.id
    add_user(uid)

    cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
    daily, budget = cursor.fetchone()

    if not has_subscription(uid) and daily >= FREE_AI_LIMIT:
        pay_url = create_payment(uid)
        bot.send_message(uid, f"💳 اشترك الآن:\n{pay_url}")
        return

    reply, cost = call_ai(m.text)

    cursor.execute("""
        UPDATE users SET
        daily_ai = daily_ai + 1,
        budget = CASE WHEN budget>0 THEN budget-? ELSE budget END
        WHERE user_id=?
    """, (cost, uid))
    conn.commit()

    bot.send_message(uid, reply)

# ======================
# WEBHOOK
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
        bot.send_message(uid, "✅ تم تفعيل اشتراكك لمدة 30 يوم")

    return jsonify({"ok": True})

# ======================
# RUN
# ======================
def run():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run, daemon=True).start()
bot.infinity_polling(skip_pending=True)
