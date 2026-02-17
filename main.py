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
SUBSCRIBER_BUDGET = 6.0   # داخلي فقط – لا يظهر للمستخدم
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
        SET subscription_until=?,
            budget=?
        WHERE user_id=?
    """, (expire, SUBSCRIBER_BUDGET, user_id))
    conn.commit()
    return expire

# ======================
# Stage 11 — Payment Instructions
# ======================
def payment_instructions_message():
    return (
        "💳 Payment Instructions (Important)\n"
        "Send USDT via TRC20 network only.\n\n"
        "Supported platforms:\n"
        "- Binance\n"
        "- OKX\n"
        "- Bybit\n"
        "- Trust Wallet\n"
        "- MetaMask\n\n"
        "⚠️ Sending via a wrong network may result in loss of funds.\n\n"
        f"🔗 {PAYMENT_URL}\n\n"
        "----------------------------------\n"
        "💳 تعليمات الدفع (مهم)\n"
        "أرسل USDT عبر شبكة TRC20 فقط.\n\n"
        "المنصات والمحافظ المدعومة:\n"
        "- Binance\n"
        "- OKX\n"
        "- Bybit\n"
        "- Trust Wallet\n"
        "- MetaMask\n\n"
        "⚠️ الإرسال عبر شبكة خاطئة قد يؤدي إلى فقدان الأموال.\n\n"
        f"🔗 {PAYMENT_URL}"
    )

# ======================
# Messages
# ======================
def budget_exhausted_message():
    return (
        "✨ You’ve reached your monthly AI limit.\n"
        "Thank you for using Zentra AI — you can renew anytime to continue.\n\n"
        "✨ لقد وصلت إلى الحد الشهري لاستخدام الذكاء الاصطناعي.\n"
        "شكرًا لاستخدامك Zentra AI — يمكنك التجديد في أي وقت للمتابعة."
    )

def subscription_required_message():
    return payment_instructions_message()

def subscription_activated_message(expire):
    date = datetime.fromtimestamp(expire).strftime("%Y-%m-%d")
    return (
        "✅ Subscription activated successfully\n"
        f"📅 Valid until: {date}\n\n"
        "✅ تم تفعيل الاشتراك بنجاح\n"
        f"📅 ينتهي بتاريخ: {date}"
    )

# ======================
# Stage 5 — AI Detector
# ======================
def is_ai_request(text):
    return text.lower().startswith("/ai")

# ======================
# Stage 8 — Math Detector
# ======================
def is_math_expression(text):
    return re.fullmatch(r"\s*\d+\s*[+\-*/]\s*\d+\s*", text)

def solve_math(text):
    try:
        a, op, b = re.findall(r"\d+|[+\-*/]", text)
        a, b = int(a), int(b)
        if op == "+": return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op == "/": return a / b
    except:
        return None

# ======================
# Stage 9 — OpenAI Engine
# ======================
def call_openai(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message["content"].strip()
    except:
        return (
            "❌ AI Error\n"
            "Try again later.\n\n"
            "❌ حدث خطأ في الذكاء الاصطناعي\n"
            "حاول لاحقًا"
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

    # Admin Stats
    if text.lower() == "zentra ai" and uid == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(total_messages) FROM users")
        messages = cursor.fetchone()[0] or 0
        uptime = int((time.time() - START_TIME) / 60)

        bot.send_message(
            message.chat.id,
            f"📊 Zentra AI – Admin Stats\n"
            f"👥 Users: {users}\n"
            f"✉️ Messages: {messages}\n"
            f"⏱ Uptime: {uptime} min\n\n"
            f"📊 إحصائيات Zentra AI\n"
            f"👥 المستخدمين: {users}\n"
            f"✉️ الرسائل: {messages}\n"
            f"⏱ مدة التشغيل: {uptime} دقيقة"
        )
        return

    # Math
    if is_math_expression(text):
        result = solve_math(text)
        if result is not None:
            bot.send_message(
                message.chat.id,
                f"🧮 Result: {result}\n🧮 النتيجة: {result}"
            )
            return

    # AI
    if is_ai_request(text):
        reset_daily_if_needed(uid)
        cursor.execute("SELECT daily_ai, budget FROM users WHERE user_id=?", (uid,))
        daily_used, budget = cursor.fetchone()

        if not has_active_subscription(uid):
            if daily_used >= FREE_AI_LIMIT:
                bot.send_message(message.chat.id, subscription_required_message())
                return
        else:
            if budget <= 0:
                bot.send_message(message.chat.id, budget_exhausted_message())
                return

        cursor.execute("""
            UPDATE users
            SET daily_ai = daily_ai + 1,
                total_messages = total_messages + 1,
                budget = CASE
                    WHEN budget > 0 THEN budget - ?
                    ELSE budget
                END
            WHERE user_id=?
        """, (AI_COST, uid))
        conn.commit()

        reply = call_openai(text[3:].strip())
        bot.send_message(message.chat.id, reply)
        return

    # Normal message
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
        bot.send_message(user_id, subscription_activated_message(expire))

    return jsonify({"ok": True})

# ======================
# Run
# ======================
def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()
bot.infinity_polling(skip_pending=True)
