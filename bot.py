from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import os
import psycopg2
import asyncio
from datetime import date, timedelta

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 1092687569

# ================= DB =================
conn = psycopg2.connect(DATABASE_URL)
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

# ================= STATE =================
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

    await update.message.reply_text(
        "👋 *Benvenuto!*\n\n"
        "✅ Registrato correttamente\n\n"
        "🔥 Riceverai aggiornamenti e offerte",
        parse_mode="Markdown"
    )

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🧹 Pulizia", callback_data="clean")]
    ]

    await update.message.reply_text("🔧 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= BUTTON =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("click_"):
        button = query.data.replace("click_", "")
        cursor.execute("INSERT INTO clicks (user_id, button) VALUES (%s,%s)",
                       (query.from_user.id, button))
        conn.commit()

# ================= ADMIN BUTTONS =================
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    if uid != ADMIN_ID:
        return

    today = date.today()

    # STATS
    if query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active = %s", (today,))
        active = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active < %s", (today - timedelta(days=7),))
        inactive = cursor.fetchone()[0]

        cursor.execute("SELECT button, COUNT(*) FROM clicks GROUP BY button")
        clicks = cursor.fetchall()

        text = f"👥 Totali: {total}\n🔥 Attivi: {active}\n💤 Inattivi: {inactive}\n\n📊 Click:\n"
        for c in clicks:
            text += f"{c[0]}: {c[1]}\n"

        await query.message.reply_text(text)

    # CLEAN
    elif query.data == "clean":
        limit = today - timedelta(days=30)

        cursor.execute("DELETE FROM users WHERE last_active < %s", (limit,))
        removed = cursor.rowcount
        conn.commit()

        await query.message.reply_text(f"🧹 Rimossi inattivi: {removed}")

    # BROADCAST
    elif query.data == "broadcast":
        user_state[uid] = "filter"
        await query.message.reply_text(
            "🎯 Scegli target:\n\n"
            "tutti\nattivi\nnuovi"
        )

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update_activity(uid)

    today = date.today()

    # FILTRO
    if user_state.get(uid) == "filter":
        text = update.message.text.lower()

        if text == "tutti":
            broadcast_data[uid] = "all"
        elif text == "attivi":
            broadcast_data[uid] = "active"
        elif text == "nuovi":
            broadcast_data[uid] = "new"

        user_state[uid] = "msg"
        await update.message.reply_text("📢 Invia messaggio")
        return

    # MSG
    if user_state.get(uid) == "msg":
        broadcast_data[uid] = {
            "type": broadcast_data[uid],
            "chat_id": update.effective_chat.id,
            "message_id": update.message.message_id
        }

        user_state[uid] = "buttons"
        await update.message.reply_text("Bottoni o 'no'")
        return

    # BUTTONS
    if user_state.get(uid) == "buttons":
        text = update.message.text
        keyboard = []

        if text.lower() != "no":
            for i, line in enumerate(text.split("\n")):
                try:
                    t, u = line.split(" - ")
                    keyboard.append([
                        InlineKeyboardButton(t, callback_data=f"click_{i}"),
                        InlineKeyboardButton("🔗", url=u)
                    ])
                except:
                    pass

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        data = broadcast_data[uid]

        # filtro utenti
        if data["type"] == "all":
            cursor.execute("SELECT user_id FROM users")
        elif data["type"] == "active":
            cursor.execute("SELECT user_id FROM users WHERE last_active = %s", (today,))
        elif data["type"] == "new":
            cursor.execute("SELECT user_id FROM users WHERE join_date = %s", (today,))

        users = cursor.fetchall()

        sent = 0
        failed = 0

        for (u,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=u,
                    from_chat_id=data["chat_id"],
                    message_id=data["message_id"],
                    reply_markup=reply_markup
                )
                sent += 1
                await asyncio.sleep(0.05)
            except:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (u,))
                conn.commit()
                failed += 1

        user_state[uid] = None

        await update.message.reply_text(f"✅ {sent} inviati\n❌ {failed} rimossi")

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(admin_buttons))
app.add_handler(CallbackQueryHandler(buttons, pattern="^click_"))

app.add_handler(MessageHandler(filters.ALL, handle))

app.run_polling()
