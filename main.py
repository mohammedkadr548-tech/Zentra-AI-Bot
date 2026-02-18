import os
import time
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
import threading
import base64
from openai import OpenAI

# ======================
# Stage 1 — Basic Setup
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ADMIN_ID = 326193841
PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085"

FREE_AI_LIMIT = 3
SUBSCRIPTION_DAYS = 30
SUBSCRIBER_BUDGET = 6.0
AI_COST = 0.10

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise Exception("Missing ENV variables")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

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

def user_exists(uid):
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (uid,))
    return cursor.fetchone() is not None

def add_user(uid):
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, joined_at, last_daily_reset, budget)
        VALUES (?, ?, ?, ?)
    """, (uid, now(), now(), 0.0))
    conn.commit()

def reset_daily_if_needed(uid):
    cursor.execute("SELECT last_daily_reset FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    if row and now() - row[0] >= 86400:
        cursor.execute("""
            UPDATE users
            SET daily_ai=0, last_daily_reset=?
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
        UPDATE users
        SET subscription_until=?, budget=?
        WHERE user_id=?
    """, (expire, SUBSCRIBER_BUDGET, uid))
    conn.commit()
    return expire

# ======================
# Messages
# ======================
def payment_message():
    return (
        "💳 Payment Instructions\n"
        "Send USDT via TRC20 only.\n\n"
        "Supported:\n"
        "- Binance\n- OKX\n- Bybit\n- Trust Wallet\n- MetaMask\n\n"
        f"{PAYMENT_URL}\n\n"
        "------------------\n"
        "💳 تعليمات الدفع\n"
        "أرسل USDT عبر TRC20 فقط.\n\n"
        f"{PAYMENT_URL}"
    )

def budget_done():
    return (
        "✨ You’ve reached your monthly AI limit.\n"
        "You can renew anytime.\n\n"
        "✨ لقد وصلت إلى الحد الشهري.\n"
        "يمكنك التجديد في أي وقت."
    )

# ======================
# OpenAI — Text + Vision
# ======================
def ask_ai(text, image_bytes=None):
    content = []

    if text:
        content.append({"type": "text", "text": text})

    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode()
        content.append({
            "type": "input_image",
            "image_base64": b64
        })

    response = client.responses.create(
        model="gpt-4.1",
        input=[{
            "role": "user",
            "content": content
        }]
    )
    return response.output_text

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
        "🤖 Just write or send a photo.\n\n"
        "👋 مرحبًا بك في Zentra AI\n"
        "🤖 اكتب أو أرسل صورة وسأرد"
    )

@bot.message_handler(content_types=["text", "photo"])
def all_messages(message):
    uid = message.from_user.id
    if not user_exists(uid):
        add_user(uid)

    reset_daily_if_needed(uid)
    cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
    daily_used, budget = cursor.fetchone()

    if not has_subscription(uid):
        if daily_used >= FREE_AI_LIMIT:
            bot.send_message(message.chat.id, payment_message())
            return
    else:
        if budget <= 0:
            bot.send_message(message.chat.id, budget_done())
            return

    image_bytes = None
    text = message.text or ""

    if message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        image_bytes = bot.download_file(file_info.file_path)

    cursor.execute("""
        UPDATE users
        SET daily_ai = daily_ai + 1,
            total_messages = total_messages + 1,
            budget = CASE WHEN budget > 0 THEN budget - ? ELSE budget END
        WHERE user_id=?
    """, (AI_COST, uid))
    conn.commit()

    reply = ask_ai(text, image_bytes)
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
        bot.send_message(uid, f"✅ Subscription active until {datetime.fromtimestamp(expire).date()}")
    return jsonify({"ok": True})

# ======================
# Run
# ======================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling(skip_pending=True)
