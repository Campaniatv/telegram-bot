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
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# ================= STATI =================
user_state = {}
temp_cmd = {}
temp_text = {}
broadcast_data = {}

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

    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if cursor.fetchone():
        msg = "✅ Bot già attivo!"
    else:
        cursor.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
        conn.commit()
        msg = "✅ Benvenuto! Bot attivato!"

    await update.message.reply_text(msg, reply_markup=main_menu())

# ================= CALLBACK =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        await query.message.edit_text("🏠 Menu", reply_markup=main_menu())

    elif query.data == "info":
        await query.message.edit_text("ℹ️ Informazioni bot", reply_markup=back_menu())

    elif query.data == "contatti":
        await query.message.edit_text("📞 @CAMPANIAVIP", reply_markup=back_menu())

    elif query.data == "canali":
        keyboard = [
            [InlineKeyboardButton("🎬 Film", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
        ]
        await query.message.edit_text("📢 Canali", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    today = datetime.now() - timedelta(days=1)
    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= %s", (today,))
    today_users = cursor.fetchone()[0]

    month = datetime.now() - timedelta(days=30)
    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= %s", (month,))
    month_users = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👑 ADMIN\n\n👥 Totali: {total}\n📅 Oggi: {today_users}\n📆 Mese: {month_users}"
    )

# ================= SETCMD =================
async def setcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Usa /setcmd nome")
        return

    cmd = context.args[0].lower()
    temp_cmd[update.effective_user.id] = cmd
    user_state[update.effective_user.id] = "cmd_text"

    await update.message.reply_text(f"✍️ Testo per /{cmd}")

# ================= DELCMD =================
async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        return

    cmd = context.args[0].lower()
    cursor.execute("DELETE FROM custom_commands WHERE command=%s", (cmd,))
    conn.commit()

    await update.message.reply_text(f"🗑️ /{cmd} eliminato!")

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast_msg"
    await update.message.reply_text("📢 Invia messaggio broadcast (testo/foto/video)")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    # ===== COMANDI CUSTOM =====
    if state == "cmd_text":
        temp_text[user_id] = update.message.text
        user_state[user_id] = "cmd_buttons"

        await update.message.reply_text("➕ Bottoni?\nNome - link\nOppure skip")
        return

    if state == "cmd_buttons":
        cmd = temp_cmd[user_id]
        buttons = update.message.text if update.message.text.lower() != "skip" else ""

        cursor.execute("""
        INSERT INTO custom_commands (command, response, buttons)
        VALUES (%s,%s,%s)
        ON CONFLICT (command) DO UPDATE SET
        response=EXCLUDED.response,
        buttons=EXCLUDED.buttons
        """, (cmd, temp_text[user_id], buttons))

        conn.commit()
        user_state[user_id] = None

        await update.message.reply_text(f"✅ /{cmd} salvato!")
        return

    # ===== BROADCAST =====
    if state == "broadcast_msg":
        broadcast_data[user_id] = update.message
        user_state[user_id] = "broadcast_buttons"

        await update.message.reply_text("➕ Bottoni?\nNome - link\nOppure skip")
        return

    if state == "broadcast_buttons":
        buttons_raw = update.message.text if update.message.text.lower() != "skip" else ""

        keyboard = []
        if buttons_raw:
            for line in buttons_raw.split("\n"):
                if " - " in line:
                    name, url = line.split(" - ", 1)
                    keyboard.append([InlineKeyboardButton(name, url=url)])

        markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0

        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=broadcast_data[user_id].chat_id,
                    message_id=broadcast_data[user_id].message_id,
                    reply_markup=markup
                )
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass

        user_state[user_id] = None

        await update.message.reply_text(f"✅ Broadcast inviato a {sent} utenti!")
        return

# ================= CUSTOM COMMAND =================
async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text[1:].split()[0]

    cursor.execute("SELECT response, buttons FROM custom_commands WHERE command=%s", (cmd,))
    res = cursor.fetchone()

    if res:
        text, buttons_raw = res

        keyboard = []
        if buttons_raw:
            for line in buttons_raw.split("\n"):
                if " - " in line:
                    name, url = line.split(" - ", 1)
                    keyboard.append([InlineKeyboardButton(name, url=url)])

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("setcmd", setcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.COMMAND, custom_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ULTRA PRO ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
