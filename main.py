import os
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "✅ البوت شغّال الآن\nاكتب أي رسالة وسأرد عليك"
    )

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.send_message(
        message.chat.id,
        f"📩 وصلتني رسالتك:\n{message.text}"
    )

bot.infinity_polling(skip_pending=True)
