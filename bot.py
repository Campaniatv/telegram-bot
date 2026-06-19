import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DB =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS custom_commands (
    command TEXT PRIMARY KEY,
    response TEXT,
    buttons TEXT
)
""")
conn.commit()

# ================= MEMORY =================
user_state = {}
temp_cmd = {}
temp_text = {}

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("⚙️ Admin", callback_data="admin_panel")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Aggiungi comando", callback_data="addcmd")],
        [InlineKeyboardButton("🗑 Elimina comando", callback_data="delcmd")],
        [InlineKeyboardButton("🔙 Menu", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit()

    text = (
        "👋 *Benvenuto!*\n\n"
        "✅ Bot attivo\n\n"
        "📢 Canali aggiornati\n"
        "📞 Contatti diretti\n\n"
        "👇 Usa i pulsanti"
    )

    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # ===== CANALI =====
    if query.data == "canali":
        await query.message.edit_text(
            "📢 *I nostri canali:*\n\n"
            "🎬 Film / Serie / Sport\n"
            "⚽ Solo Sport",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Film / Serie", url="https://t.me/+HLygUda0f_wwNmE0")],
                [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
                [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
            ]),
            parse_mode="Markdown"
        )

    # ===== CONTATTI =====
    elif query.data == "contatti":
        await query.message.edit_text(
            "📞 *Contattaci subito:*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/393509741712")],
                [InlineKeyboardButton("📩 Telegram", url="https://t.me/CAMPANIAVIP")],
                [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
            ]),
            parse_mode="Markdown"
        )

    # ===== ADMIN PANEL =====
    elif query.data == "admin_panel":
        if user_id != ADMIN_ID:
            return
        await query.message.edit_text("⚙️ *Pannello Admin*", reply_markup=admin_menu(), parse_mode="Markdown")

    elif query.data == "back":
        await query.message.edit_text("🏠 Menu", reply_markup=main_menu())

    # ===== STATS =====
    elif query.data == "stats":
        if user_id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        await query.message.reply_text(f"📊 Utenti totali: {total}")

    # ===== BROADCAST =====
    elif query.data == "broadcast":
        if user_id != ADMIN_ID:
            return
        user_state[user_id] = "broadcast"
        await query.message.reply_text("📢 Invia messaggio")

    # ===== ADD CMD =====
    elif query.data == "addcmd":
        if user_id != ADMIN_ID:
            return
        user_state[user_id] = "cmd_name"
        await query.message.reply_text("Nome comando (senza /)")

    # ===== DEL CMD =====
    elif query.data == "delcmd":
        if user_id != ADMIN_ID:
            return
        user_state[user_id] = "delcmd"
        await query.message.reply_text("Nome comando da eliminare")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = user_state.get(user_id)

    # ADD CMD
    if state == "cmd_name":
        temp_cmd[user_id] = text.lower()
        user_state[user_id] = "cmd_text"
        await update.message.reply_text("Testo comando")
        return

    elif state == "cmd_text":
        temp_text[user_id] = text
        user_state[user_id] = "cmd_buttons"
        await update.message.reply_text("Bottoni? nome,link oppure skip")
        return

    elif state == "cmd_buttons":
        buttons = None if text.lower() == "skip" else text

        cursor.execute("""
        INSERT INTO custom_commands (command, response, buttons)
        VALUES (%s, %s, %s)
        ON CONFLICT (command) DO UPDATE
        SET response = EXCLUDED.response,
            buttons = EXCLUDED.buttons
        """, (temp_cmd[user_id], temp_text[user_id], buttons))

        conn.commit()
        user_state[user_id] = None
        await update.message.reply_text("✅ Salvato")
        return

    # DELETE CMD
    elif state == "delcmd":
        cursor.execute("DELETE FROM custom_commands WHERE command = %s", (text.lower(),))
        conn.commit()
        user_state[user_id] = None
        await update.message.reply_text("🗑 Eliminato")
        return

    # BROADCAST
    elif state == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.id
                )
            except:
                pass

        user_state[user_id] = None
        await update.message.reply_text("✅ Inviato")
        return

# ================= CUSTOM =================
async def handle_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text.startswith("/"):
        return

    cmd = text.split()[0][1:]

    cursor.execute("SELECT response, buttons FROM custom_commands WHERE command = %s", (cmd,))
    result = cursor.fetchone()

    if result:
        response, buttons = result

        keyboard = None
        if buttons:
            rows = []
            for b in buttons.split("|"):
                name, link = b.split(",")
                rows.append([InlineKeyboardButton(name.strip(), url=link.strip())])
            keyboard = InlineKeyboardMarkup(rows)

        await update.message.reply_text(response, reply_markup=keyboard)

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/"), handle_custom))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ BOT ULTRA PRO ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
