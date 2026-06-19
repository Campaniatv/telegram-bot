import os
import asyncio
import psycopg2
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from telegram.error import Forbidden, BadRequest

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DATABASE =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

def setup_database():
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

setup_database()

# ================= UTENTI =================
def add_user(user):
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user.id,))
    exists = cursor.fetchone()

    if exists:
        cursor.execute("""
        UPDATE users SET last_active = CURRENT_TIMESTAMP
        WHERE user_id = %s
        """, (user.id,))
        conn.commit()
        return False  # già esiste
    else:
        cursor.execute("""
        INSERT INTO users (user_id, first_name, last_name, username)
        VALUES (%s, %s, %s, %s)
        """, (user.id, user.first_name, user.last_name, user.username))
        conn.commit()
        return True  # nuovo

def update_active(user_id):
    cursor.execute("""
    UPDATE users SET last_active = CURRENT_TIMESTAMP
    WHERE user_id = %s
    """, (user_id,))
    conn.commit()

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Promo", callback_data="promo")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("📱 App", callback_data="app")]
    ])

def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Indietro", callback_data="home")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_new = add_user(user)

    msg = "✅ Bot attivo!" if is_new else "⚡ Bot già attivo!"

    await update.message.reply_text(
        f"{msg}\n\nScegli:",
        reply_markup=main_menu()
    )

# ================= COMANDI =================
async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 PROMO ATTIVE:\n\nScrivici per offerte VIP")

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
    )

async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
        [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")]
    ]

    await update.message.reply_text(
        "📢 CANALI UFFICIALI:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def app_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 APP disponibile a breve 🚀")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    if query.data == "home":
        await query.edit_message_text("🏠 Menu:", reply_markup=main_menu())

    elif query.data == "promo":
        await query.edit_message_text("🔥 PROMO ATTIVE", reply_markup=back())

    elif query.data == "canali":
        keyboard = [
            [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="home")]
        ]
        await query.edit_message_text("📢 CANALI UFFICIALI:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "contatti":
        keyboard = [
            [InlineKeyboardButton("💬 Telegram", url="https://t.me/CAMPANIAVIP")],
            [InlineKeyboardButton("📱 WhatsApp", url="https://wa.me/+393509741712")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="home")]
        ]
        await query.edit_message_text("📞 CONTATTI:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "app":
        await query.edit_message_text("📱 APP disponibile a breve", reply_markup=back())

    elif query.data == "stats" and uid == ADMIN_ID:
        today = date.today()

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at) = %s", (today,))
        today_count = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE DATE_TRUNC('month', joined_at) = DATE_TRUNC('month', CURRENT_DATE)
        """)
        month = cursor.fetchone()[0]

        await query.edit_message_text(
            f"📊 STATISTICHE\n\n"
            f"👥 Totali: {total}\n"
            f"🔥 Oggi: {today_count}\n"
            f"📅 Mese: {month}",
            reply_markup=back()
        )

    elif query.data == "broadcast" and uid == ADMIN_ID:
        context.user_data["broadcast"] = True
        await query.edit_message_text("📢 Invia messaggio broadcast", reply_markup=back())

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    await update.message.reply_text("🔧 ADMIN", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= BROADCAST =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_active(uid)

    if context.user_data.get("broadcast") and uid == ADMIN_ID:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0

        for (user_id,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                sent += 1
                await asyncio.sleep(0.05)

            except Forbidden:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                conn.commit()
                removed += 1

            except BadRequest:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                conn.commit()
                removed += 1

        context.user_data["broadcast"] = False

        await update.message.reply_text(
            f"✅ Inviati: {sent}\n🧹 Rimossi: {removed}"
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("app", app_cmd))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE PERFETTO")
    app.run_polling()

if __name__ == "__main__":
    main()
