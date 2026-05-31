from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import os
import sqlite3

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569

# 🔹 DATABASE
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# 🔹 STATO UTENTE (broadcast)
user_state = {}

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("📞 Info", callback_data="info")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✨ *Benvenuto!*\n\n"
        "🔔 Riceverai:\n"
        "• Guasti in tempo reale\n"
        "• Aggiornamenti\n"
        "• Promozioni\n\n"
        "⚠️ Controlla di avere le notifiche attive!\n\n"
        "👇 Scegli un'opzione:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# 🔹 INFO (comando)
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
    )

# 🔹 CONTATTI (alias)
async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await info(update, context)

# 🔹 BOTTONI
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.message.reply_text(
            "📞 CONTATTI:\n\n"
            "Telegram: https://t.me/CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/+393509741712"
        )

    elif query.data == "canali":
        await query.message.reply_text(
            "📢 CANALI:\n\n"
            "🎬 Film/Serie/Sport:\n"
            "https://t.me/+HLygUda0f_wwNmE0\n\n"
            "⚽ Solo sport:\n"
            "https://t.me/+Xv4kd5Uja0YzY2M0"
        )

# 🔹 UTENTI TOTALI
async def utenti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"👥 Utenti totali: {count}")

# 🔹 UTENTI OGGI
async def oggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE DATE(created_at) = CURRENT_DATE
    """)
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"📈 Nuovi oggi: {count}")

# 🔹 BROADCAST STEP 1
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato")
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia ORA il messaggio (testo, foto, video...)")

# 🔹 BROADCAST STEP 2
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_state.get(user_id) != "broadcast":
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0

    for user in users:
        try:
            await context.bot.copy_message(
                chat_id=user[0],
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            sent += 1
        except:
            pass

    user_state[user_id] = None
    await update.message.reply_text(f"✅ Inviato a {sent} utenti")

# 🔹 PANNELLO ADMIN
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "⚙️ PANNELLO ADMIN\n\n"
        "/broadcast - invia messaggio\n"
        "/utenti - totale utenti\n"
        "/oggi - nuovi oggi"
    )

# 🔹 SETUP BOT
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("utenti", utenti))
    app.add_handler(CommandHandler("oggi", oggi))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("✅ Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()
