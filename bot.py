from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")

# lista utenti (semplice in memoria)
users = set()

# 🔹 START: salva utenti
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.add(user_id)

    await update.message.reply_text(
        "👋 Benvenuto! Sei registrato per ricevere messaggi."
    )

# 🔹 BROADCAST: invia messaggio a tutti
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # SOLO TU puoi usarlo (metti il tuo ID Telegram)
    ADMIN_ID = 1092687569  # <-- cambia con il tuo ID

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato")
        return

    message = " ".join(context.args)

    if not message:
        await update.message.reply_text("Scrivi: /broadcast messaggio")
        return

    sent = 0
    for user_id in list(users):
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"Messaggio inviato a {sent} utenti")

# 🔹 SETUP BOT
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))

app.run_polling()