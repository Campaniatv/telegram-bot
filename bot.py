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

# ================= DATABASE =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY
)
""")

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
temp_buttons = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")]
    ]

    text = (
        "👋 *Benvenuto!*\n\n"
        "✅ Bot attivo\n\n"
        "👇 Usa i pulsanti:"
    )

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "contatti":
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/393509741712")],
            [InlineKeyboardButton("📢 Telegram", url="https://t.me/")]
        ]
        await query.message.reply_text("📞 Contattaci:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "canali":
        await query.message.reply_text("📢 I nostri canali presto disponibili")

# ================= SETCMD =================
async def setcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Usa: /setcmd nome")
        return

    cmd = context.args[0].lower()

    temp_cmd[update.effective_user.id] = cmd
    user_state[update.effective_user.id] = "text"

    await update.message.reply_text(f"✍️ Testo per /{cmd}")

# ================= DELCMD =================
async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Usa: /delcmd nome")
        return

    cmd = context.args[0].lower()

    cursor.execute("DELETE FROM custom_commands WHERE command = %s", (cmd,))
    conn.commit()

    await update.message.reply_text(f"🗑️ /{cmd} eliminato")

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia il messaggio")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    state = user_state.get(user_id)

    # ===== CREAZIONE COMANDO =====
    if state == "text":
        temp_text[user_id] = text
        user_state[user_id] = "buttons"
        await update.message.reply_text("➕ Bottoni?\nNome,link | Nome,link\nOppure scrivi skip")
        return

    elif state == "buttons":
        if text.lower() == "skip":
            temp_buttons[user_id] = None
        else:
            temp_buttons[user_id] = text

        cmd = temp_cmd[user_id]
        response = temp_text[user_id]
        buttons = temp_buttons[user_id]

        cursor.execute("""
        INSERT INTO custom_commands (command, response, buttons)
        VALUES (%s, %s, %s)
        ON CONFLICT (command) DO UPDATE
        SET response = EXCLUDED.response,
            buttons = EXCLUDED.buttons
        """, (cmd, response, buttons))
        conn.commit()

        user_state[user_id] = None

        await update.message.reply_text(f"✅ /{cmd} salvato")
        return

    # ===== BROADCAST =====
    elif state == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0

        for u in users:
            uid = u[0]
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.id
                )
                sent += 1
            except Exception as e:
                if "blocked" in str(e).lower():
                    cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                    conn.commit()
                    removed += 1

        user_state[user_id] = None

        await update.message.reply_text(f"✅ Inviati: {sent}\n🚫 Rimossi: {removed}")
        return

# ================= CUSTOM COMMANDS =================
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
            btns = []
            for b in buttons.split("|"):
                name, link = b.split(",")
                btns.append([InlineKeyboardButton(name.strip(), url=link.strip())])
            keyboard = InlineKeyboardMarkup(btns)

        await update.message.reply_text(response, reply_markup=keyboard)

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setcmd", setcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(buttons))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/"), handle_custom))

    print("✅ BOT ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
