import os
import asyncio
import psycopg2

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ DATABASE
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT
)
""")
conn.commit()

user_state = {}

# ✅ SALVA UTENTE
def add_user(user):
    cursor.execute("""
    INSERT INTO users (user_id, first_name, last_name, username)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (user_id) DO NOTHING
    """, (user.id, user.first_name, user.last_name, user.username))
    conn.commit()

# ✅ START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)

    keyboard = [
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")]
    ]

    await update.message.reply_text(
        "✅ Bot attivo!\n\nUsa i bottoni o i comandi.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ✅ INFO
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ INFO\n\nBot aggiornamenti automatici."
    )

# ✅ CONTATTI
async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
    )

# ✅ ADMIN
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🔧 ADMIN\n\n/broadcast\n/stats"
    )

# ✅ BROADCAST
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia messaggio")

# ✅ STATS
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    await update.message.reply_text(f"👥 Utenti: {total}")

# ✅ BOTTONI
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.message.reply_text("ℹ️ INFO\n\nBot aggiornamenti automatici.")

    elif query.data == "contatti":
        await query.message.reply_text(
            "📞 CONTATTI:\n\n"
            "Telegram: https://t.me/CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/+393509741712"
        )

# ✅ MESSAGGI
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user_state.get(user.id) == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                await asyncio.sleep(0.05)
            except:
                pass

        user_state[user.id] = None
        await update.message.reply_text("✅ Inviato")

# ✅ MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    # ✅ COMANDI
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("info", info))          # ✅ FIX
    app.add_handler(CommandHandler("contatti", contatti))  # ✅ FIX

    # ✅ BOTTONI
    app.add_handler(CallbackQueryHandler(buttons))

    # ✅ MESSAGGI (NON BLOCCA COMANDI)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("🔥 BOT ONLINE")

    app.run_polling()

if __name__ == "__main__":
    main()