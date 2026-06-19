from telegram.ext import CommandHandler, ContextTypes
from telegram import Update

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Benvenuto! Usa /admin per gestire il bot.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Questo è un bot Telegram personalizzato!")

def setup_commands(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    # Aggiungi altri comandi qui...
