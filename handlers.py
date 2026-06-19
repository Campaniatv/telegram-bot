from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from commands import start, info, canali, contatti
from admin import admin, stats, broadcast, aggiungi_comando, elimina_comando
from database import add_user, update_active, get_custom_command
from utils import is_admin

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.edit_message_text(
            "ℹ️ INFO\n\n"
            "In questo canale troverai comunicazioni ufficiali, aggiornamenti, avvisi e promozioni pubblicate periodicamente.\n\n"
            "Resta iscritto per non perdere nessuna novità."
        )

    elif query.data == "canali":
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎬 Film / Serie / Sport",
                    url="https://t.me/+HLygUda0f_wwNmE0"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚽ Solo Sport",
                    url="https://t.me/+Xv4kd5Uja0YzY2M0"
                )
            ]
        ]
        await query.edit_message_text(
            "📢 CANALI UFFICIALI\n\n"
            "🎬 Film, Serie TV e Sport\n"
            "⚽ Solo Sport\n\n"
            "Scegli il canale che preferisci:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "contatti":
        await query.edit_message_text(
            "📞 CONTATTI:\n\n"
            "Telegram: https://t.me/CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/393509741712"
        )

    elif query.data == "stats":
        if not is_admin(update.effective_user.id):
            return
        await stats(update, context)

    elif query.data == "broadcast":
        if not is_admin(update.effective_user.id):
            return
        await broadcast(update, context)

    elif query.data == "add_command":
        if not is_admin(update.effective_user.id):
            return
        await aggiungi_comando(update, context)

    elif query.data == "del_command":
        if not is_admin(update.effective_user.id):
            return
        await elimina_comando(update, context)

def setup_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_messages))

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_active(user_id)

    if user_id in context.user_data.get("broadcast", {}):
        await handle_broadcast(update, context)
        return

    if update.message.text and update.message.text.startswith("/"):
        cmd = update.message.text[1:].split()[0]
        response = get_custom_command(cmd)
        if response:
            await update.message.reply_text(response)
            return

    if not update.message.text.startswith("/"):
        await update.message.reply_text("👋 Usa /start per vedere le opzioni!")
