from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import os
import psycopg2
import asyncio

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 1092687569

# 🔹 DATABASE
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY
)
""")
conn.commit()

# 🔹 STATO
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

    await update.message.reply_text(
        "👋 Sei registrato!\n\nScegli un'opzione:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 🔹 INFO
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
    )

# 🔹 CANALI
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 CANALI:\n\n"
        "🎬 Film/Serie/Sport:\n"
        "https://t.me/+HLygUda0f_wwNmE0\n\n"
        "⚽ Solo sport:\n"
        "https://t.me/+Xv4kd5Uja0YzY2M0"
    )

# 🔹 BOTTONI NORMALI
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await info(update, context)

    elif query.data == "canali":
        await canali(update, context)

    elif query.data == "admin_utenti":
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await query.message.reply_text(f"👥 Utenti: {count}")

    elif query.data == "admin_broadcast":
        user_state[query.from_user.id] = "broadcast"
        await query.message.reply_text("📢 Invia il messaggio da mandare a tutti")

# 🔹 PANNELLO ADMIN
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("👥 Utenti", callback_data="admin_utenti")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
    ]

    await update.message.reply_text(
        "⚙️ Pannello Admin",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 🔹 BROADCAST
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_state.get(user_id) != "broadcast":
        return

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

            # ✅ ANTI BAN (pausa)
            await asyncio.sleep(0.05)

        except:
            pass

    user_state[user_id] = None
    await update.message.reply_text(f"✅ Inviato a {sent} utenti")

# 🔹 COMANDI
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("canali", canali))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.ALL, handle_message))

print("✅ Bot online con sistema PRO")
app.run_polling()
