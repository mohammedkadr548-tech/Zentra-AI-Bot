import os
import time
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
import threading

# ======================
# Stage 1 — Basic Setup
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 326193841
PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085"

FREE_AI_LIMIT = 3
SUBSCRIPTION_DAYS = 30

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is not set")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
START_TIME = time.time()

print("Zentra AI bot started")

# ======================
# Stage 3 — Database
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
    subscription_until INTEGER DEFAULT 0
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
        (user_id, joined_at, last_daily_reset)
        VALUES (?, ?, ?)
    """, (user_id, now(), now()))
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
    cursor.execute(
        "SELECT subscription_until FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row and row[0] > now()

def activate_subscription(user_id):
    expire = now() + SUBSCRIPTION_DAYS * 86400
    cursor.execute("""
        UPDATE users
        SET subscription_until=?
        WHERE user_id=?
    """, (expire, user_id))
    conn.commit()
    return expire

# ======================
# Messages
# ======================
def subscription_required_message():
    return (
        "🚫 Free AI limit reached\n"
        "Subscribe to continue using AI:\n"
        f"{PAYMENT_URL}\n\n"
        "🚫 لقد انتهى الحد المجاني للذكاء الاصطناعي\n"
        "اشترك لمتابعة الاستخدام:\n"
        f"{PAYMENT_URL}"
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
# Stage 5 + 6 — AI Gate
# ======================
def is_ai_request(text):
    return text.lower().startswith("/ai")

# ======================
# Handlers (ONE ONLY)
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    if not user_exists(uid):
        add_user(uid)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Zentra AI\n"
        "✅ Bot is active\n\n"
        "👋 مرحبًا بك في Zentra AI\n"
        "✅ البوت يعمل بشكل صحيح"
    )

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    uid = message.from_user.id
    text = message.text or ""

    if not user_exists(uid):
        add_user(uid)

    # ======================
    # Admin Stats
    # ======================
    if text.lower() == "zentra ai" and uid == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(total_messages) FROM users")
        total_msgs = cursor.fetchone()[0] or 0

        uptime = int((time.time() - START_TIME) / 60)

        bot.send_message(
            message.chat.id,
            f"📊 Zentra AI – Admin Stats\n"
            f"👥 Total users: {users_count}\n"
            f"✉️ Total messages: {total_msgs}\n"
            f"⏱ Uptime: {uptime} min\n\n"
            f"📊 إحصائيات Zentra AI\n"
            f"👥 المستخدمين: {users_count}\n"
            f"✉️ الرسائل: {total_msgs}\n"
            f"⏱ مدة التشغيل: {uptime} دقيقة"
        )
        return

    # ======================
    # AI Requests
    # ======================
    if is_ai_request(text):
        reset_daily_if_needed(uid)

        if not has_active_subscription(uid):
            cursor.execute(
                "SELECT daily_ai FROM users WHERE user_id=?",
                (uid,)
            )
            used = cursor.fetchone()[0]

            if used >= FREE_AI_LIMIT:
                bot.send_message(message.chat.id, subscription_required_message())
                return

        cursor.execute("""
            UPDATE users
            SET daily_ai = daily_ai + 1,
                total_messages = total_messages + 1
            WHERE user_id = ?
        """, (uid,))
        conn.commit()

        bot.send_message(
            message.chat.id,
            "🤖 AI request received\n"
            "🤖 تم استلام طلب الذكاء الاصطناعي"
        )
        return

    # ======================
    # Normal Message
    # ======================
    cursor.execute(
        "UPDATE users SET total_messages = total_messages + 1 WHERE user_id=?",
        (uid,)
    )
    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ Bot is active\n"
        "✅ البوت يعمل بشكل صحيح"
    )

# ======================
# Stage 7 — NOWPayments Webhook
# ======================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"ok": False})

    if data.get("payment_status") == "finished":
        user_id = int(data.get("order_id"))
        if not user_exists(user_id):
            add_user(user_id)

        expire = activate_subscription(user_id)
        bot.send_message(
            user_id,
            subscription_activated_message(expire)
        )

    return jsonify({"ok": True})

# ======================
# Run
# ======================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling(skip_pending=True)
