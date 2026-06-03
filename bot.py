import os
import asyncio
import psycopg2
from datetime import datetime, timedelta

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
        username = EXCLUDED.username
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

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("SELECT joined_at, last_active FROM users WHERE user_id = %s", (user.id,))
    data = cursor.fetchone()

    now = datetime.utcnow()

    if data:
        last_active = data[1]

        # ✅ bentornato se inattivo da 2 giorni
        if last_active and (now - last_active) > timedelta(days=2):
            text = (
                "👋 *Bentornato!*\n\n"
                "Ci sei mancato 😄\n"
                "Il bot è sempre attivo ✅\n\n"
                "👇 Usa i pulsanti qui sotto:"
            )
        else:
            text = (
                "✅ *Bot già attivo!*\n\n"
                "Sei già registrato 👍\n\n"
                "👇 Usa i pulsanti qui sotto:"
            )
    else:
        text = (
            "👋 *Benvenuto!*\n\n"
            "✅ Ora il bot è attivo!\n\n"
            "Riceverai:\n"
            "🔧 Guasti\n"
            "📢 Aggiornamenti\n"
            "🎁 Promozioni\n\n"
            "👇 Usa i pulsanti qui sotto:"
        )

    add_user(user)
    update_active(user.id)

    await update.message.reply_text(
        text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= COMANDI =================
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *I nostri canali:*\n\n👉 https://t.me/AggiornamentiCampaniabot",
        parse_mode="Markdown"
    )

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Contatti:*\n\nTelegram: https://t.me/CAMPANIAVIP",
        parse_mode="Markdown"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🔧 *Pannello Admin*",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia il messaggio (testo, foto, video...)")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "canali":
        await query.message.edit_text(
            "📢 *Canali:*\n\n👉 https://t.me/AggiornamentiCampaniabot",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Indietro", callback_data="back")]]),
            parse_mode="Markdown"
        )

    elif query.data == "contatti":
        await query.message.edit_text(
            "📞 *Contatti:*\n\nTelegram: https://t.me/CAMPANIAVIP",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Indietro", callback_data="back")]]),
            parse_mode="Markdown"
        )

    elif query.data == "back":
        if user_id == ADMIN_ID:
            await query.message.edit_text("🔧 *Pannello Admin*", reply_markup=admin_menu(), parse_mode="Markdown")
        else:
            await query.message.edit_text("🏠 *Menu principale*", reply_markup=main_menu(), parse_mode="Markdown")

    elif query.data == "stats":
        if user_id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_DATE")
        today = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= date_trunc('month', CURRENT_DATE)")
        month = cursor.fetchone()[0]

        await query.message.reply_text(
            f"📊 *Statistiche*\n\n👥 Totali: {total}\n📅 Oggi: {today}\n🗓 Mese: {month}",
            parse_mode="Markdown"
        )

    elif query.data == "broadcast":
        if user_id != ADMIN_ID:
            return

        user_state[user_id] = "broadcast"
        await query.message.reply_text("📢 Invia ora il messaggio")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_active(user_id)

    if user_state.get(user_id) == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0
        errors = 0

        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                sent += 1
                await asyncio.sleep(0.05)

            except Exception as e:
                error_text = str(e).lower()

                if "blocked" in error_text or "forbidden" in error_text:
                    cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                    conn.commit()
                    removed += 1
                else:
                    errors += 1

        user_state[user_id] = None

        await update.message.reply_text(
            f"✅ Inviato: {sent}\n🚫 Bloccato bot: {removed}\n⚠️ Errori: {errors}"
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE PERFETTO")
    app.run_polling()

if __name__ == "__main__":
    main()
