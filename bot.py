from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, CallbackQueryHandler
)
import os
import psycopg2
from datetime import datetime, timedelta
import asyncio

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 1092687569

# 🔹 DB
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    first_seen TIMESTAMP,
    last_active TIMESTAMP,
    messages INT DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS scheduled (
    id SERIAL PRIMARY KEY,
    message TEXT,
    send_at TIMESTAMP
)
""")

conn.commit()

# 🔹 SALVA UTENTE
def save_user(user_id):
    now = datetime.now()

    cursor.execute("""
    INSERT INTO users (user_id, first_seen, last_active, messages)
    VALUES (%s, %s, %s, 1)
    ON CONFLICT (user_id)
    DO UPDATE SET
    last_active = %s,
    messages = users.messages + 1
    """, (user_id, now, now, now))

    conn.commit()

# 🔹 MENU
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📞 Contatti", callback_data="info")]
    ])

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)

    await update.message.reply_text(
        "🔥 *Benvenuto nel bot ufficiale*\n\nRiceverai aggiornamenti esclusivi 🚀",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# 🔹 ADMIN PANEL
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("⏰ Programma", callback_data="schedule")],
        [InlineKeyboardButton("🧹 Pulizia", callback_data="clean")]
    ]

    await update.message.reply_text(
        "⚙️ ADMIN PANEL ULTRA",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 🔹 CALLBACK
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        return

    now = datetime.now()

    if query.data == "stats":
        today = now.date()
        month = now - timedelta(days=30)
        active = now - timedelta(days=7)

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE first_seen::date=%s", (today,))
        today_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE first_seen >= %s", (month,))
        month_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active >= %s", (active,))
        active_users = cursor.fetchone()[0]

        await query.message.reply_text(
            f"📊 STATISTICHE\n\n"
            f"👥 Totali: {total}\n"
            f"🆕 Oggi: {today_users}\n"
            f"📅 Mese: {month_users}\n"
            f"🔥 Attivi: {active_users}"
        )

    elif query.data == "broadcast":
        context.user_data["broadcast"] = True
        await query.message.reply_text("Invia messaggio")

    elif query.data == "schedule":
        context.user_data["schedule"] = True
        await query.message.reply_text("Scrivi: testo | minuti")

    elif query.data == "clean":
        cursor.execute("DELETE FROM users WHERE last_active < NOW() - INTERVAL '30 days'")
        conn.commit()
        await query.message.reply_text("Utenti puliti ✅")

# 🔹 HANDLE
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)

    # 🔹 BROADCAST
    if context.user_data.get("broadcast") and user_id == ADMIN_ID:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0

        for u in users:
            try:
                await context.bot.copy_message(
                    chat_id=u[0],
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                sent += 1
                await asyncio.sleep(0.07)
            except:
                cursor.execute("DELETE FROM users WHERE user_id=%s", (u[0],))
                conn.commit()

        await update.message.reply_text(f"Inviato a {sent}")
        context.user_data["broadcast"] = False

    # 🔹 SCHEDULE
    elif context.user_data.get("schedule") and user_id == ADMIN_ID:
        try:
            text, minutes = update.message.text.split("|")
            send_time = datetime.now() + timedelta(minutes=int(minutes))

            cursor.execute(
                "INSERT INTO scheduled (message, send_at) VALUES (%s, %s)",
                (text.strip(), send_time)
            )
            conn.commit()

            await update.message.reply_text("Programmato ✅")
        except:
            await update.message.reply_text("Formato: testo | minuti")

        context.user_data["schedule"] = False

# 🔹 TASK SCHEDULER
async def scheduler(app):
    while True:
        now = datetime.now()

        cursor.execute("SELECT id, message FROM scheduled WHERE send_at <= %s", (now,))
        jobs = cursor.fetchall()

        for job in jobs:
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()

            for u in users:
                try:
                    await app.bot.send_message(chat_id=u[0], text=job[1])
                    await asyncio.sleep(0.05)
                except:
                    pass

            cursor.execute("DELETE FROM scheduled WHERE id=%s", (job[0],))
            conn.commit()

        await asyncio.sleep(30)

# 🔹 MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL, handle))

    app.job_queue.run_once(lambda ctx: asyncio.create_task(scheduler(app)), 1)

    print("🔥 BOT ULTRA ONLINE")

    app.run_polling()

if __name__ == "__main__":
    main()
