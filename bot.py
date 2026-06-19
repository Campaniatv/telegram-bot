import os
import asyncio
import psycopg2

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

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")]
    ])

def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Indietro", callback_data="home")]
    ])

# ================= STATO =================
user_state = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)

    await update.message.reply_text(
        "👋 Benvenuto!\n\nScegli un'opzione:",
        reply_markup=main_menu()
    )

# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "home":
        await query.edit_message_text(
            "🏠 Menu principale:",
            reply_markup=main_menu()
        )

    elif query.data == "info":
        await query.edit_message_text(
            "ℹ️ INFO\n\nResta aggiornato su tutte le novità.",
            reply_markup=back()
        )

    elif query.data == "canali":
        keyboard = [
            [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="home")]
        ]
        await query.edit_message_text("📢 CANALI:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "contatti":
    keyboard = [
        [InlineKeyboardButton("💬 Telegram", url="https://t.me/CAMPANIAVIP")],
        [InlineKeyboardButton("📱 WhatsApp", url="https://wa.me/393509741712")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="home")]
    ]

    await query.edit_message_text(
        "📞 CONTATTI\n\nScegli come contattarci:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


    elif query.data == "stats":
        if update.effective_user.id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        await query.edit_message_text(f"👥 Utenti: {total}")

    elif query.data == "broadcast":
        if update.effective_user.id != ADMIN_ID:
            return

        user_state[update.effective_user.id] = "broadcast"

        await query.edit_message_text("📢 Invia il messaggio da mandare a tutti")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    await update.message.reply_text(
        "🔧 ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BROADCAST =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_active(user_id)

    if user_state.get(user_id) == "broadcast":
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
                await asyncio.sleep(0.08)

            except Forbidden:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                conn.commit()
                removed += 1

            except BadRequest as e:
                if "chat not found" in str(e):
                    cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                    conn.commit()
                    removed += 1

            except Exception as e:
                print(f"Errore {uid}: {e}")

        user_state[user_id] = None

        await update.message.reply_text(
            f"✅ Inviati: {sent}\n🧹 Rimossi: {removed}"
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE LIVELLO 100")
    app.run_polling()

if __name__ == "__main__":
    main()
