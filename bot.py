import os
import asyncio
import psycopg2

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

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
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

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

# ================= STATO =================
user_state = {}

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)

    await update.message.reply_text(
        "✅ *Bot attivo!*\n\n"
        "Grazie per averci scelto 🙏\n\n"
        "Riceverai:\n"
        "🔧 Guasti\n"
        "📢 Aggiornamenti\n"
        "🎁 Promozioni\n\n"
        "👇 Usa i pulsanti qui sotto:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= COMANDI =================
async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/393509741712"
    )

async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
        [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ]

    await update.message.reply_text(
        "📢 CANALI UFFICIALI\n\nScegli:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "canali":
        keyboard = [
            [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
        ]

        await query.edit_message_text(
            "📢 CANALI UFFICIALI\n\nScegli:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "contatti":
        await query.edit_message_text(
            "📞 CONTATTI:\n\n"
            "Telegram: https://t.me/CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/393509741712"
        )

    elif query.data == "back":
        await query.edit_message_text(
            "👋 Menu principale:",
            reply_markup=main_menu()
        )

    elif query.data == "stats":
        if update.effective_user.id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '1 day'")
        today = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '30 days'")
        month = cursor.fetchone()[0]

        await query.edit_message_text(
            f"📊 STATISTICHE\n\n👥 Totali: {total}\n🔥 Oggi: {today}\n📅 Mese: {month}"
        )

    elif query.data == "broadcast":
        if update.effective_user.id != ADMIN_ID:
            return

        user_state[update.effective_user.id] = "broadcast"

        await query.edit_message_text("📢 Invia ora il messaggio")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    await update.message.reply_text(
        "🔧 PANNELLO ADMIN",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"

    await update.message.reply_text("📢 Invia messaggio")

# ================= HANDLE =================
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
                await asyncio.sleep(0.05)
            except:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                conn.commit()
                removed += 1

        user_state[user_id] = None

        await update.message.reply_text(
            f"✅ Inviato: {sent}\n🧹 Rimossi: {removed}"
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE PERFETTO")
    app.run_polling()

if __name__ == "__main__":
    main()
