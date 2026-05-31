from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import os
import psycopg2

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# 🔹 DB
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    active BOOLEAN DEFAULT TRUE
)
""")
conn.commit()

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")]
    ]

    await update.message.reply_text(
        "✨ Benvenuto!\n\nClicca il bottone sotto 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 🔹 INFO
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\nTelegram: https://t.me/CAMPANIAVIP\nWhatsApp: https://wa.me/+393509741712"
    )

# 🔹 CALLBACK
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.message.reply_text(
            "📞 CONTATTI:\n\nTelegram: https://t.me/CAMPANIAVIP\nWhatsApp: https://wa.me/+393509741712"
        )

# 🔹 BROADCAST
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text("Scrivi il messaggio da inviare:")
    context.user_data["broadcast"] = True

# 🔹 INVIO BROADCAST
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("broadcast"):
        cursor.execute("SELECT user_id FROM users WHERE active = TRUE")
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

        await update.message.reply_text(f"Inviato a {sent} utenti ✅")
        context.user_data["broadcast"] = False

# 🔹 UTENTI
async def utenti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    await update.message.reply_text(f"👥 Utenti totali: {total}")

# 🔹 MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("utenti", utenti))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
