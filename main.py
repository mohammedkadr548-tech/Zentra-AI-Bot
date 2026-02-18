import os
import time
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
import threading
import openai

# ======================
# Stage 1 — Basic Setup
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Missing BOT_TOKEN or OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

ADMIN_ID = 326193841
PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085"

FREE_AI_LIMIT = 3
SUBSCRIPTION_DAYS = 30
SUBSCRIBER_BUDGET = 6.0  # داخلي فقط

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# ======================
# Stage 2 — Database
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
# Stage 3 — Helpers
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
    return expire

# ======================
# Stage 4 — Messages
# ======================
WELCOME_MESSAGE = (
    "👋 Welcome to Zentra AI\n"
    "🤖 Just write anything and I’ll reply.\n\n"
    "👋 مرحبًا بك في Zentra AI\n"
    "🤖 اكتب أي شيء وسأرد عليك مباشرة"
)

def payment_message():
    return (
        "💳 Subscribe to continue using Zentra AI\n"
        f"{PAYMENT_URL}\n\n"
        "💳 اشترك لمتابعة استخدام Zentra AI\n"
        f"{PAYMENT_URL}"
    )

def budget_end_message():
    return (
        "✨ You’ve reached your monthly AI limit.\n"
        "Thank you for using Zentra AI.\n\n"
        "✨ لقد وصلت إلى الحد الشهري.\n"
        "شكرًا لاستخدامك Zentra AI."
    )

# ======================
# Stage 5 — OpenAI (Text)
# ======================
def call_ai_text(prompt):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700
        )
        reply = res.choices[0].message["content"]
        cost = (res.usage.total_tokens / 1000) * 0.002
        return reply, cost
    except:
        return "❌ AI error\n\n❌ خطأ في الذكاء الاصطناعي", 0

# ======================
# Stage 6 — OpenAI (Image)
# ======================
def call_ai_image(image_url, prompt):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=700
        )
        reply = res.choices[0].message["content"]
        cost = (res.usage.total_tokens / 1000) * 0.002
        return reply, cost
    except:
        return "❌ Image analysis error\n\n❌ خطأ في تحليل الصورة", 0

# ======================
# Stage 7 — Handlers
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    add_user(message.from_user.id)
    bot.send_message(message.chat.id, WELCOME_MESSAGE)

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    uid = message.from_user.id
    add_user(uid)
    reset_daily(uid)

    cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
    daily, budget = cursor.fetchone()

    if not has_subscription(uid) and daily >= FREE_AI_LIMIT:
        bot.send_message(message.chat.id, payment_message())
        return
    if has_subscription(uid) and budget <= 0:
        bot.send_message(message.chat.id, budget_end_message())
        return

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

    prompt = message.caption or "Explain this image"
    reply, cost = call_ai_image(image_url, prompt)

    cursor.execute("""
        UPDATE users
        SET daily_ai=daily_ai+1,
            budget=CASE WHEN budget>0 THEN budget-? ELSE budget END
        WHERE user_id=?
    """, (cost, uid))
    conn.commit()

    bot.send_message(message.chat.id, reply)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    add_user(uid)
    reset_daily(uid)

    cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
    daily, budget = cursor.fetchone()

    if not has_subscription(uid) and daily >= FREE_AI_LIMIT:
        bot.send_message(message.chat.id, payment_message())
        return
    if has_subscription(uid) and budget <= 0:
        bot.send_message(message.chat.id, budget_end_message())
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
# Stage 8 — Webhook & Run
# ======================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data and data.get("payment_status") == "finished":
        uid = int(data.get("order_id"))
        add_user(uid)
        activate_subscription(uid)
        bot.send_message(uid, "✅ Subscription activated\n\n✅ تم تفعيل الاشتراك")
    return jsonify(ok=True)

def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask, daemon=True).start()
bot.infinity_polling(skip_pending=True)
