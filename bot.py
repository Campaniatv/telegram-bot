import os
import asyncio
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

WHATSAPP_LINK = "https://wa.me/393509741712"
TELEGRAM_CONTACT = "https://t.me/CAMPANIAVIP"

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

# ================= STATE =================
user_state = {}
temp_cmd = {}
temp_text = {}

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("⚙️ Comandi", callback_data="cmd_menu")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

# ================= UTENTI =================
def add_user(user_id):
    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    await update.message.reply_text(
        "👋 Benvenuto!",
        reply_markup=main_menu()
    )

# ================= CONTATTI/CANALI =================
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Film", url="https://t.me/+HLygUda0f_wwNmE0")],
        [InlineKeyboardButton("⚽ Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")]
    ]
    await update.message.reply_text("📢 Canali:", reply_markup=InlineKeyboardMarkup(keyboard))

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 Telegram", url=TELEGRAM_CONTACT)],
        [InlineKeyboardButton("📱 WhatsApp", url=WHATSAPP_LINK)]
    ]
    await update.message.reply_text("📞 Contatti:", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text("🔧 Admin", reply_markup=admin_menu())

# ================= SETCMD =================
async def setcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Usa: /setcmd nome")
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

    await update.message.reply_text(f"🗑️ /{cmd} eliminato")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "canali":
        keyboard = [
            [InlineKeyboardButton("🎬 Film", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
        ]
        await query.message.edit_text("📢 Canali:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "contatti":
        keyboard = [
            [InlineKeyboardButton("💬 Telegram", url=TELEGRAM_CONTACT)],
            [InlineKeyboardButton("📱 WhatsApp", url=WHATSAPP_LINK)],
            [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
        ]
        await query.message.edit_text("📞 Contatti:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "cmd_menu":
        await query.message.reply_text("Usa:\n/setcmd nome\n/delcmd nome")

    elif query.data == "broadcast":
        user_state[user_id] = "broadcast"
        await query.message.reply_text("📢 Invia messaggio")

    elif query.data == "back":
        await query.message.edit_text("🏠 Menu", reply_markup=main_menu())

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ===== COMANDI CUSTOM =====
    if user_state.get(user_id) == "cmd_text":
        temp_text[user_id] = update.message.text
        user_state[user_id] = "cmd_buttons"
        await update.message.reply_text("➕ Bottoni?\nNome - link\nOppure scrivi skip")
        return

    if user_state.get(user_id) == "cmd_buttons":
        cmd = temp_cmd[user_id]
        buttons = update.message.text if update.message.text.lower() != "skip" else ""

        cursor.execute("""
        INSERT INTO custom_commands (command, response, buttons)
        VALUES (%s,%s,%s)
        ON CONFLICT (command) DO UPDATE SET response=%s, buttons=%s
        """, (cmd, temp_text[user_id], buttons, temp_text[user_id], buttons))

        conn.commit()
        user_state[user_id] = None

        await update.message.reply_text(f"✅ /{cmd} salvato")
        return

    # ===== BROADCAST =====
    if user_state.get(user_id) == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0

        for (u,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=u,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                sent += 1
                await asyncio.sleep(0.04)

            except Exception as e:
                if "blocked" in str(e).lower():
                    cursor.execute("DELETE FROM users WHERE user_id=%s", (u,))
                    conn.commit()
                    removed += 1

        user_state[user_id] = None

        await update.message.reply_text(
            f"✅ Inviati: {sent}\n🚫 Rimossi: {removed}"
        )
        return

    # ===== ESECUZIONE COMANDI CUSTOM =====
    if update.message.text:
        text = update.message.text.replace("/", "").lower()

        cursor.execute("SELECT response, buttons FROM custom_commands WHERE command=%s", (text,))
        result = cursor.fetchone()

        if result:
            response, buttons = result

            keyboard = []
            if buttons:
                for line in buttons.split("\n"):
                    if " - " in line:
                        name, link = line.split(" - ")
                        keyboard.append([InlineKeyboardButton(name, url=link)])

            await update.message.reply_text(
                response,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("setcmd", setcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT PRO ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
