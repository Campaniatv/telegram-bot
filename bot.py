from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import os
import psycopg2

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# 🔹 CONNESSIONE POSTGRES
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# 🔹 CREA TABELLA
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY
)
""")
conn.commit()

# 🔹 STATO UTENTE
user_state = {}

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute(
        "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (user_id,)
    )
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

# 🔹 COMANDI INFO / CONTATTI
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
    )

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
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

# 🔹 BROADCAST
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia ORA il messaggio da inviare a tutti")

# 🔹 INVIO MESSAGGI
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_state.get(user_id) != "broadcast":
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0

    for user in users:
        try:
            await context.bot.copy_message(
                chat_id=user[0],
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Messaggio inviato a {sent} utenti")

    user_state[user_id] = None

# 🔹 CONTA UTENTI
async def utenti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"👥 Utenti: {count}")

# 🔹 AVVIO
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("contatti", contatti))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("utenti", utenti))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.ALL, handle_message))

app.run_polling()
