from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import os
import sqlite3

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569

# 🔹 DATABASE
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# 🔹 STATO UTENTE (per broadcast)
user_state = {}

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("📞 Info", callback_data="info")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Sei registrato! Riceverai gli aggiornamenti.\n\nScegli un'opzione:",
        reply_markup=reply_markup
    )

# 🔹 BOTTONI
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.message.reply_text(
            "📞 CONTATTI:\n\n"
            "Telegram: https://t.me/CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/+393509741712"
        )

    elif query.data == "canali":
        await query.message.reply_text(
            "📢 CANALI:\n\n"
            "🎬 Film/Serie/Sport:\n"
            "https://t.me/+HLygUda0f_wwNmE0\n\n"
            "⚽ Solo sport:\n"
            "https://t.me/+Xv4kd5Uja0YzY2M0"
        )

# 🔹 COMANDO BROADCAST (STEP 1)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato")
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia ORA il messaggio (testo, foto, video...)")

# 🔹 RICEZIONE MESSAGGIO (STEP 2)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_state.get(user_id) != "broadcast":
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0

    for (uid,) in users:
        try:
            # 🔥 copia qualsiasi tipo di messaggio
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            sent += 1
        except:
            pass

    user_state[user_id] = None
    await update.message.reply_text(f"✅ Inviato a {sent} utenti")

# 🔹 SETUP BOT
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CallbackQueryHandler(button_handler))

# 👇 QUESTO È IMPORTANTISSIMO
app.add_handler(MessageHandler(filters.ALL, handle_message))

app.run_polling()
