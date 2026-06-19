import os
import psycopg2
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from telegram.error import Forbidden

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DATABASE =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS commands (
    name TEXT PRIMARY KEY,
    response TEXT
)
""")

conn.commit()

# ================= STATE =================
user_state = {}

# ================= UTENTI =================
def add_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=%s",(user_id,))
    if cursor.fetchone():
        return False
    cursor.execute("INSERT INTO users (user_id) VALUES (%s)",(user_id,))
    conn.commit()
    return True

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Promo", callback_data="promo")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("📱 App", callback_data="app")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Indietro", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new = add_user(user_id)

    text = "✅ Bot attivo!" if new else "⚡ Bot già attivo!"

    await update.message.reply_text(text, reply_markup=main_menu())

# ================= CALLBACK BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = update.effective_user.id

    # ===== MENU PRINCIPALE =====
    if q.data == "back":
        await q.edit_message_text("🏠 Menu principale", reply_markup=main_menu())

    elif q.data == "promo":
        await q.edit_message_text(
            "🔥 PROMO ESCLUSIVE\n\n🎬 Film + Sport\n⚡ Accesso immediato\n💎 Qualità top",
            reply_markup=back_button()
        )

    elif q.data == "canali":
        keyboard = [
            [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="back")]
        ]
        await q.edit_message_text("📢 CANALI UFFICIALI", reply_markup=InlineKeyboardMarkup(keyboard))

    elif q.data == "contatti":
        await q.edit_message_text(
            "📞 CONTATTI\n\nTelegram: https://t.me/CAMPANIAVIP\nWhatsApp: https://wa.me/+393509741712",
            reply_markup=back_button()
        )

    elif q.data == "app":
        await q.edit_message_text(
            "📱 APP IN ARRIVO 🚀",
            reply_markup=back_button()
        )

    # ===== ADMIN =====
    elif q.data == "admin":
        if user_id != ADMIN_ID:
            return

        keyboard = [
            [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="back")]
        ]
        await q.edit_message_text("👑 PANNELLO ADMIN", reply_markup=InlineKeyboardMarkup(keyboard))

    elif q.data == "stats":
        if user_id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        today = datetime.now().date()
        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at)=%s",(today,))
        today_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE_TRUNC('month', joined_at)=DATE_TRUNC('month', CURRENT_DATE)")
        month_count = cursor.fetchone()[0]

        await q.edit_message_text(
            f"📊 STATISTICHE\n\n👥 Totali: {total}\n🔥 Oggi: {today_count}\n📆 Mese: {month_count}",
            reply_markup=back_button()
        )

    elif q.data == "broadcast":
        if user_id != ADMIN_ID:
            return

        user_state[user_id] = "broadcast"

        await q.edit_message_text(
            "📢 Invia ora messaggio / foto / video",
            reply_markup=back_button()
        )

# ================= BROADCAST =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_state.get(user_id) == "broadcast":
        user_state[user_id] = None

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent, removed = 0, 0

        for (uid,) in users:
            try:
                if update.message.text:
                    await context.bot.send_message(uid, update.message.text)
                elif update.message.photo:
                    await context.bot.send_photo(uid, update.message.photo[-1].file_id, caption=update.message.caption)
                elif update.message.video:
                    await context.bot.send_video(uid, update.message.video.file_id, caption=update.message.caption)

                sent += 1

            except Forbidden:
                cursor.execute("DELETE FROM users WHERE user_id=%s",(uid,))
                conn.commit()
                removed += 1

        await update.message.reply_text(f"✅ Inviati: {sent}\n❌ Rimossi: {removed}")
        return

# ================= ADMIN COMMAND =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("👑 Apri Admin", callback_data="admin")]
    ]

    await update.message.reply_text("🔧 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT FIXATO PERFETTO")
    app.run_polling()

if __name__ == "__main__":
    main()
