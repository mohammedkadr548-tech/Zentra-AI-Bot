import sqlite3
import time

# =========================
# Database connection
# =========================
conn = sqlite3.connect("zentra_ai.db", check_same_thread=False)
cursor = conn.cursor()

# =========================
# Create users table
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    total_messages INTEGER DEFAULT 0,
    daily_messages INTEGER DEFAULT 0,
    last_daily_reset INTEGER DEFAULT 0,
    joined_at INTEGER
)
""")
conn.commit()

# =========================
# Helpers
# =========================
def now():
    return int(time.time())

def create_user(user_id: int):
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, joined_at, last_daily_reset)
        VALUES (?, ?, ?)
    """, (user_id, now(), now()))
    conn.commit()

def user_exists(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def increase_message_count(user_id: int):
    cursor.execute("""
        UPDATE users
        SET total_messages = total_messages + 1,
            daily_messages = daily_messages + 1
        WHERE user_id=?
    """, (user_id,))
    conn.commit()

def reset_daily_if_needed(user_id: int):
    cursor.execute(
        "SELECT last_daily_reset FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        return

    if now() - row[0] >= 86400:
        cursor.execute("""
            UPDATE users
            SET daily_messages = 0,
                last_daily_reset = ?
            WHERE user_id=?
        """, (now(), user_id))
        conn.commit()

def get_daily_messages(user_id: int) -> int:
    cursor.execute(
        "SELECT daily_messages FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else 0
