import os
import time
import sqlite3
import telebot

# ======================
# Basic Setup
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
    joined_at INTEGER
)
""")
conn.commit()

# ======================
# Helper Functions
# ======================
def user_exists(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def add_user(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, ?)",
        (user_id, int(time.time()))
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

    # ❌ لا reply_to
    # ✅ send_message فقط
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

    # ❌ لا reply_to
    # ❌ لا اقتباس
    # ❌ لا اسم مستخدم
    bot.send_message(
        message.chat.id,
        "✅ Bot is active\n"
        "✅ البوت يعمل بشكل صحيح"
    )

# ======================
# Run Bot
# ======================
bot.infinity_polling(skip_pending=True)
