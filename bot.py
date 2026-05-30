from telegram import Update
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

# 🔹 START (salva utente nel database)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    await update.message.reply_text(
        "👋 Sei registrato! Riceverai gli aggiornamenti."
    )

# 🔹 BROADCAST (solo admin)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ADMIN_ID = 1092687569  # <-- METTI QUI IL TUO ID

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
app.add_handler(CommandHandler("broadcast", broadcast))

app.run_polling()