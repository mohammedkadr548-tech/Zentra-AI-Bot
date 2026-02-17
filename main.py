import os
import time
import sqlite3
import telebot

# ======================
# Basic Setup
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 326193841  # ← غيّرها إذا لزم

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN is not set")

bot = telebot.TeleBot(BOT_TOKEN)
START_TIME = time.time()

print("✅ Zentra AI bot started")

# ======================
# Database (SQLite)
# ======================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined_at INTEGER,
    total_messages INTEGER DEFAULT 0,
    daily_messages INTEGER DEFAULT 0,
    last_daily_reset INTEGER
)
""")
conn.commit()

# ======================
# Helper Functions
# ======================
def now():
    return int(time.time())

def user_exists(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def add_user(user_id: int):
    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, joined_at, last_daily_reset)
        VALUES (?, ?, ?)
        """,
        (user_id, now(), now())
    )
    conn.commit()

def reset_daily_if_needed(user_id: int):
    cursor.execute(
        "SELECT last_daily_reset FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    if row and now() - row[0] >= 86400:
        cursor.execute(
            """
            UPDATE users
            SET daily_messages = 0,
                last_daily_reset = ?
            WHERE user_id = ?
            """,
            (now(), user_id)
        )
        conn.commit()

def increase_message_count(user_id: int):
    reset_daily_if_needed(user_id)
    cursor.execute(
        """
        UPDATE users
        SET total_messages = total_messages + 1,
            daily_messages = daily_messages + 1
        WHERE user_id = ?
        """,
        (user_id,)
    )
    conn.commit()

# ======================
# Handlers
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    if not user_exists(user_id):
        add_user(user_id)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Zentra AI\n"
        "✅ Bot is active\n\n"
        "👋 مرحبًا بك في Zentra AI\n"
        "✅ البوت يعمل بشكل صحيح"
    )

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.from_user.id

    if not user_exists(user_id):
        add_user(user_id)

    increase_message_count(user_id)

    # 📊 أمر الإحصائيات (للأدمن فقط)
    if message.text.lower() == "zentra ai" and user_id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(total_messages) FROM users")
        total_messages = cursor.fetchone()[0] or 0

        uptime_minutes = int((time.time() - START_TIME) / 60)

        bot.send_message(
            message.chat.id,
            f"📊 Zentra AI – Admin Stats\n"
            f"👥 Total users: {total_users}\n"
            f"✉️ Total messages: {total_messages}\n"
            f"⏱ Uptime: {uptime_minutes} min\n\n"
            f"📊 إحصائيات Zentra AI\n"
            f"👥 المستخدمين: {total_users}\n"
            f"✉️ الرسائل: {total_messages}\n"
            f"⏱ مدة التشغيل: {uptime_minutes} دقيقة"
        )
        return

    bot.send_message(
        message.chat.id,
        "✅ Bot is active\n"
        "✅ البوت يعمل بشكل صحيح"
    )

# ======================
# Run Bot
# ======================
bot.infinity_polling(skip_pending=True)
# ======================
# Stage 4 - Free AI Limit
# ======================

FREE_AI_LIMIT = 3  # عدد طلبات الذكاء الاصطناعي المجانية لكل مستخدم خلال 24 ساعة

def can_use_free_ai(user_id: int) -> bool:
    """
    يتحقق هل المستخدم ما زال ضمن الحد المجاني للذكاء الاصطناعي
    """
    reset_daily_if_needed(user_id)

    cursor.execute(
        "SELECT daily_messages FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row:
        return False

    return row[0] < FREE_AI_LIMIT


def free_limit_message():
    """
    رسالة تظهر عند انتهاء الحد المجاني
    """
    return (
        "🚫 Free AI limit reached\n"
        "Subscribe to continue using AI features.\n\n"
        "🚫 لقد انتهى الحد المجاني للذكاء الاصطناعي\n"
        "اشترك لمتابعة استخدام الميزات."
    )
 # ======================
# Stage 5 - AI Access + Subscription Gate
# ======================

PAYMENT_URL = "https://nowpayments.io/payment/?iid=4711328085"
FREE_AI_LIMIT = 3  # عدد رسائل الذكاء الاصطناعي المجانية

def is_ai_request(message_text: str) -> bool:
    """
    نعتبر أي رسالة تبدأ بـ /ai طلب ذكاء اصطناعي
    مثال:
    /ai hello
    """
    return message_text.lower().startswith("/ai")


def has_free_ai(user_id: int) -> bool:
    reset_daily_if_needed(user_id)
    cursor.execute(
        "SELECT daily_messages FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        return False
    return row[0] < FREE_AI_LIMIT


def subscription_message():
    return (
        "🚫 Free AI limit reached\n"
        "Subscribe to continue using AI features:\n"
        f"{PAYMENT_URL}\n\n"
        "🚫 لقد انتهى الحد المجاني للذكاء الاصطناعي\n"
        "اشترك لمتابعة استخدام الميزات:\n"
        f"{PAYMENT_URL}"
    )


# 🔁 نعدل الهاندلر الحالي (لا تنشئ واحد جديد)
@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.from_user.id
    text = message.text or ""

    if not user_exists(user_id):
        add_user(user_id)

    # 📊 إحصائيات الأدمن
    if text.lower() == "zentra ai" and user_id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(total_messages) FROM users")
        total_messages = cursor.fetchone()[0] or 0

        uptime_minutes = int((time.time() - START_TIME) / 60)

        bot.send_message(
            message.chat.id,
            f"📊 Zentra AI – Admin Stats\n"
            f"👥 Total users: {total_users}\n"
            f"✉️ Total messages: {total_messages}\n"
            f"⏱ Uptime: {uptime_minutes} min\n\n"
            f"📊 إحصائيات Zentra AI\n"
            f"👥 المستخدمين: {total_users}\n"
            f"✉️ الرسائل: {total_messages}\n"
            f"⏱ مدة التشغيل: {uptime_minutes} دقيقة"
        )
        return

    # 🤖 طلب ذكاء اصطناعي
    if is_ai_request(text):
        if not has_free_ai(user_id):
            bot.send_message(
                message.chat.id,
                subscription_message()
            )
            return

        # خصم رسالة ذكاء اصطناعي
        increase_message_count(user_id)

        # 🔹 رد مؤقت (لاحقًا نربطه بالذكاء الاصطناعي الحقيقي)
        bot.send_message(
            message.chat.id,
            "🤖 AI response\n"
            "تم استلام طلب الذكاء الاصطناعي"
        )
        return

    # 💬 رسالة عادية (لا تُحسب على الذكاء الاصطناعي)
    bot.send_message(
        message.chat.id,
        "✅ Bot is active\n"
        "✅ البوت يعمل بشكل صحيح"
    )   
