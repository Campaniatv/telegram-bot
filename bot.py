import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import logging

# Configura il logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variabili d'ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL")

# Comandi personalizzati
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Ciao! Sono un bot Telegram!")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ Non sei autorizzato!")
        return
    await update.message.reply_text("🔑 Sei un admin!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ Non sei autorizzato!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usa: /broadcast <messaggio>")
        return

    message = " ".join(context.args)
    await update.message.reply_text(f"📢 Inviando broadcast: {message}")

    # Qui aggiungerai il codice per inviare a tutti gli utenti
    await update.message.reply_text("✅ Broadcast inviato!")

# Funzione principale
async def main():
    try:
        # Crea l'applicazione
        application = Application.builder().token(BOT_TOKEN).build()

        # Aggiungi comandi
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin))
        application.add_handler(CommandHandler("broadcast", broadcast))

        # Avvia il bot
        logger.info("🚀 Avvio del bot in corso...")
        await application.run_polling()
        logger.info("✅ BOT ONLINE PERFETTO!")

    except Exception as e:
        logger.error(f"❌ Errore nel bot: {e}")
        raise

# Avvio sicuro dell'event loop
if __name__ == "__main__":
    # Questo previene il problema "event loop already running"
    if not asyncio.get_event_loop().is_running():
        asyncio.run(main())
    else:
        logger.warning("⚠️ Event loop già in esecuzione - riavvio in corso...")
        loop = asyncio.get_event_loop()
        loop.create_task(main())
