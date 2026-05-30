from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import sqlite3

TOKEN = os.getenv("BOT_TOKEN")

# 🔹 DATABASE
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Info/Contatti", callback_data="info")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Sei registrato! Riceverai gli aggiornamenti. Se hai bisogno di altro scegli un'opzione:",
        reply_markup=reply_markup
    )

# 🔹 INFO
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://t.me/+393509741712"
    )

# 🔹 CANALI
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 CANALI:\n\n"
        "🎬 Aggiornamenti sport, film e serie TV:\n"
        "https://t.me/+HLygUda0f_wwNmE0\n\n"
        "⚽ Solo sport:\n"
        "https://t.me/+Xv4kd5Uja0YzY2M0"
    )

# 🔹 BROADCAST
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ADMIN_ID = 1092687569

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato")
        return

    message = " ".join(context.args)

    if not message:
        await update.message.reply_text("Uso: /broadcast messaggio")
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0

    for (user_id,) in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Inviato a {sent} utenti")

# 🔹 SETUP
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("canali", canali))
app.add_handler(CommandHandler("broadcast", broadcast))

app.run_polling()