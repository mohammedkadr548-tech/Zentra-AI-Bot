import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Read token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Zentra AI Bot\n\n"
        "🇦🇪 أرسل عملية جمع مثل: 2+3\n"
        "🇬🇧 Send an addition like: 2+3"
    )

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(" ", "")

    # Match simple addition مثل 2+3
    match = re.fullmatch(r"(\d+)\+(\d+)", text)

    if match:
        a = int(match.group(1))
        b = int(match.group(2))
        result = a + b
        await update.message.reply_text(f"✅ Result / النتيجة: {result}")
    else:
        await update.message.reply_text(
            "❌ صيغة غير صحيحة\n"
            "اكتب مثل: 4+5\n"
            "Write like: 4+5"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Zentra AI Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
