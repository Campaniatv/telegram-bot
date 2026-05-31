import os
import asyncio
import psycopg2
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569

# ✅ DATABASE POSTGRES (Railway)
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ✅ SALVA UTENTE
def add_user(user):
    cursor.execute("""
    INSERT INTO users (user_id, first_name, last_name, username)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (user_id) DO NOTHING
    """, (user.id, user.first_name, user.last_name, user.username))
    conn.commit()

# ✅ AGGIORNA ATTIVITÀ
def update_active(user_id):
    cursor.execute("""
    UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = %s
    """, (user_id,))
    conn.commit()

# ✅ /START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)

    text = (
        "✨ *Benvenuto!*\n\n"
        "👉 t.me/AggiornamentiCampaniabot\n\n"
        "🔧 *Guasti*\n"
        "📢 *Aggiornamenti*\n"
        "🎁 *Promozioni*\n\n"
        "✅ Resta sempre aggiornato!"
    )

    keyboard = [
        [InlineKeyboardButton("🔧 Guasti", callback_data="guasti")],
        [InlineKeyboardButton("📢 Aggiornamenti", callback_data="news")],
        [InlineKeyboardButton("🎁 Promo", callback_data="promo")]
    ]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ✅ BOTTONI
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "guasti":
        await query.edit_message_text("🔧 Nessun guasto segnalato")
    elif query.data == "news":
        await query.edit_message_text("📢 Nessun aggiornamento")
    elif query.data == "promo":
        await query.edit_message_text("🎁 Nessuna promo")

# ✅ BROADCAST
user_state = {}

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia il messaggio da mandare a tutti")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)
    update_active(user.id)

    if user_state.get(user.id) == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0

        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                sent += 1
                await asyncio.sleep(0.05)  # ✅ antiban
            except:
                pass

        user_state[user.id] = None
        await update.message.reply_text(f"✅ Inviato a {sent} utenti")

# ✅ STATISTICHE
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE joined_at >= NOW() - INTERVAL '1 day'
    """)
    today = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active >= NOW() - INTERVAL '7 days'
    """)
    active = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👥 Totali: {total}\n📅 Oggi: {today}\n🔥 Attivi: {active}"
    )

# ✅ SCHEDULER (NO JOBQUEUE 🔥)
async def scheduler(app):
    while True:
        await asyncio.sleep(3600)
        print("✅ Scheduler attivo")

async def start_scheduler(app):
    asyncio.create_task(scheduler(app))

# ✅ MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    app.post_init = start_scheduler  # ✅ FIX IMPORTANTE

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL, handle))

    print("🔥 BOT ONLINE")

    app.run_polling()

if __name__ == "__main__":
    main()
