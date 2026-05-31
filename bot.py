import os
import asyncio
import psycopg2
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DB =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

def setup_database():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY
    )
    """)

    columns = [
        ("first_name", "TEXT"),
        ("last_name", "TEXT"),
        ("username", "TEXT"),
        ("joined_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("last_active", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]

    for col, tipo in columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {tipo}")
        except:
            pass

    conn.commit()

setup_database()

# ================= UTENTI =================
def add_user(user):
    cursor.execute("""
    INSERT INTO users (user_id, first_name, last_name, username)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (user_id) DO UPDATE SET
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        username = EXCLUDED.username,
        last_active = CURRENT_TIMESTAMP
    """, (user.id, user.first_name, user.last_name, user.username))
    conn.commit()

def update_active(user_id):
    cursor.execute("""
    UPDATE users SET last_active = CURRENT_TIMESTAMP
    WHERE user_id = %s
    """, (user_id,))
    conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)

    keyboard = [
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")]
    ]

    await update.message.reply_text(
        "✅ Bot attivo!\n\nScegli un'opzione:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= INFO =================
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Info bot attive")

# ================= CONTATTI =================
async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
    )

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await info(update, context)
    elif query.data == "contatti":
        await contatti(update, context)

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    await update.message.reply_text(
        "⚙️ PANNELLO ADMIN",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

user_state = {}

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia il messaggio da inviare a tutti")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_active(user_id)

    if user_state.get(user_id) != "broadcast":
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0
    removed = 0

    for (uid,) in users:
        try:
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            sent += 1
            await asyncio.sleep(0.05)  # ✅ anti-ban
        except:
            # ✅ rimuove utenti morti
            cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
            conn.commit()
            removed += 1

    user_state[user_id] = None

    await update.message.reply_text(
        f"✅ Inviato: {sent}\n🧹 Rimossi: {removed}"
    )

# ================= STATS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active > NOW() - INTERVAL '1 day'
    """)
    today = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active > NOW() - INTERVAL '30 days'
    """)
    month = cursor.fetchone()[0]

    await update.message.reply_text(
        f"📊 STATISTICHE\n\n"
        f"👥 Totali: {total}\n"
        f"🔥 Oggi: {today}\n"
        f"📅 Mese: {month}"
    )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("🔥 BOT ULTRA PRO ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
