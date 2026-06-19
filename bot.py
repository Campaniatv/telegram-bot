import os
import psycopg2
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
CREATE TABLE IF NOT EXISTS custom_commands (
    command TEXT PRIMARY KEY,
    response TEXT,
    buttons TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY
)
""")

conn.commit()

# ================= MEMORY =================
user_state = {}
temp_cmd = {}
temp_text = {}
temp_buttons = {}

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute(
        "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (user_id,)
    )
    conn.commit()

    await update.message.reply_text("🏠 Menu", reply_markup=main_menu())

# ================= CALLBACK =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        await query.message.edit_text("🏠 Menu", reply_markup=main_menu())

    elif query.data == "info":
        await query.message.edit_text("ℹ️ Informazioni del bot", reply_markup=back_menu())

    elif query.data == "canali":
        await query.message.edit_text("📢 I nostri canali", reply_markup=back_menu())

    elif query.data == "contatti":
        await query.message.edit_text("📞 Contatti admin", reply_markup=back_menu())

# ================= SETCMD =================
async def setcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Usa /setcmd nome")
        return

    cmd = context.args[0].lower()
    temp_cmd[update.effective_user.id] = cmd
    user_state[update.effective_user.id] = "text"

    await update.message.reply_text(f"✍️ Invia il testo per /{cmd}")

# ================= DELCMD =================
async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        return

    cmd = context.args[0].lower()

    cursor.execute("DELETE FROM custom_commands WHERE command=%s", (cmd,))
    conn.commit()

    await update.message.reply_text(f"🗑️ /{cmd} eliminato")

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text("📢 Invia il messaggio da mandare a tutti")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    # ===== CREAZIONE COMANDO =====
    if state == "text":
        temp_text[user_id] = update.message.text
        user_state[user_id] = "buttons"
        await update.message.reply_text("🔘 Invia bottoni (nome - link) oppure scrivi skip")
        return

    elif state == "buttons":
        buttons = None

        if update.message.text.lower() != "skip":
            try:
                name, link = update.message.text.split(" - ")
                buttons = str([[name, link]])
            except:
                await update.message.reply_text("❌ Formato: nome - link")
                return

        cursor.execute(
            "INSERT INTO custom_commands (command, response, buttons) VALUES (%s,%s,%s) "
            "ON CONFLICT (command) DO UPDATE SET response=%s, buttons=%s",
            (
                temp_cmd[user_id],
                temp_text[user_id],
                buttons,
                temp_text[user_id],
                buttons
            )
        )
        conn.commit()

        user_state[user_id] = None
        await update.message.reply_text("✅ Comando salvato!")
        return

    # ===== BROADCAST =====
    elif state == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for u in users:
            try:
                if update.message.text:
                    await context.bot.send_message(u[0], update.message.text)
                elif update.message.photo:
                    await context.bot.send_photo(u[0], update.message.photo[-1].file_id)
                elif update.message.video:
                    await context.bot.send_video(u[0], update.message.video.file_id)
            except:
                pass

        user_state[user_id] = None
        await update.message.reply_text("✅ Broadcast inviato!")
        return

    # ===== COMANDI CUSTOM =====
    if update.message.text and update.message.text.startswith("/"):
        cmd = update.message.text[1:].split()[0]

        cursor.execute("SELECT response, buttons FROM custom_commands WHERE command=%s", (cmd,))
        row = cursor.fetchone()

        if row:
            response, buttons = row

            keyboard = None
            if buttons:
                try:
                    btns = eval(buttons)
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(b[0], url=b[1])] for b in btns
                    ])
                except:
                    pass

            await update.message.reply_text(response, reply_markup=keyboard)

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setcmd", setcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, handle))

    print("✅ BOT ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()