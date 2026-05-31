from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import os
import psycopg2
import asyncio
from datetime import date, timedelta

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 1092687569

# ✅ SICUREZZA DB
if not DATABASE_URL:
    raise Exception("DATABASE_URL mancante")

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    join_date DATE,
    last_active DATE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS clicks (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    button TEXT
)
""")

conn.commit()

user_state = {}
broadcast_data = {}

# ================= UTILS =================
async def update_activity(user_id):
    today = date.today()
    cursor.execute("""
    INSERT INTO users (user_id, join_date, last_active)
    VALUES (%s, %s, %s)
    ON CONFLICT (user_id)
    DO UPDATE SET last_active = %s
    """, (user_id, today, today, today))
    conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_activity(update.effective_user.id)

    await update.message.reply_text("✅ Bot attivo")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    await update.message.reply_text("Admin", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= CALLBACK =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    if uid != ADMIN_ID:
        return

    today = date.today()

    if query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active = %s", (today,))
        active = cursor.fetchone()[0]

        await query.message.reply_text(f"Totali: {total}\nAttivi oggi: {active}")

    elif query.data == "broadcast":
        user_state[uid] = "msg"
        await query.message.reply_text("Invia messaggio")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update_activity(uid)

    if user_state.get(uid) == "msg":
        data = {
            "chat_id": update.effective_chat.id,
            "message_id": update.message.message_id
        }

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0

        for (u,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=u,
                    from_chat_id=data["chat_id"],
                    message_id=data["message_id"]
                )
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass

        user_state[uid] = None
        await update.message.reply_text(f"Inviati: {sent}")

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.ALL, handle))

app.run_polling()
