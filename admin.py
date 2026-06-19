from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_custom_command, add_custom_command,
    delete_custom_command, log_broadcast
)
from utils import is_admin

user_state = {}

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Aggiungi Comando", callback_data="add_command")],
        [InlineKeyboardButton("➖ Elimina Comando", callback_data="del_command")]
    ]

    await update.message.reply_text(
        "🔧 PANNELLO ADMIN",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    from database import get_db_connection
    conn, cursor = get_db_connection()

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active > NOW() - INTERVAL '1 day'
    """)
    today = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active > NOW() - INTERVAL '30 days'
    """)
    month = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM custom_commands")
    custom_cmds = cursor.fetchone()[0]

    await update.message.reply_text(
        f"📊 STATISTICHE\n\n"
        f"👥 Totali: {total}\n"
        f"🔥 Oggi: {today}\n"
        f"📅 Mese: {month}\n"
        f"🛠️ Comandi personalizzati: {custom_cmds}"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text(
        "📢 Invia adesso il messaggio da inviare a tutti gli utenti."
    )

async def aggiungi_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    user_state[update.effective_user.id] = "add_command"
    await update.message.reply_text(
        "📝 Invia il nome del comando (senza /) seguito dalla risposta.\n"
        "Esempio: `mio_comando Questo è il messaggio di risposta`"
    )

async def elimina_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    user_state[update.effective_user.id] = "del_command"
    await update.message.reply_text(
        "❌ Invia il nome del comando da eliminare."
    )
