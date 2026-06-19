import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

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
    button_text TEXT
)
""")

conn.commit()

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Canali", callback_data="cmd:canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="cmd:contatti")]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit()

    await update.message.reply_text(
        "🔥 Benvenuto nel bot!",
        reply_markup=main_menu()
    )

# ================= CANALI =================
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Film Serie Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
        [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

    await update.message.reply_text("📢 I nostri canali:", reply_markup=keyboard)

# ================= CONTATTI =================
async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Telegram", url="https://t.me/CAMPANIAVIP")],
        [InlineKeyboardButton("📱 WhatsApp", url="https://wa.me/393509741712")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

    await update.message.reply_text("📞 Contattaci:", reply_markup=keyboard)

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "👑 Pannello Admin:\n\n"
        "/addcmd comando risposta\n"
        "/delcmd comando\n"
        "/listcmd"
    )

# ================= ADD COMMAND =================
async def addcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        cmd = context.args[0].lower()
        response = " ".join(context.args[1:])

        cursor.execute(
            "INSERT INTO custom_commands (command, response) VALUES (%s, %s) ON CONFLICT (command) DO UPDATE SET response=%s",
            (cmd, response, response)
        )
        conn.commit()

        await update.message.reply_text(f"✅ Comando /{cmd} salvato")

    except:
        await update.message.reply_text("❌ Uso: /addcmd nome risposta")

# ================= DELETE COMMAND =================
async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cmd = context.args[0].lower()

    cursor.execute("DELETE FROM custom_commands WHERE command=%s", (cmd,))
    conn.commit()

    await update.message.reply_text(f"🗑️ Comando {cmd} eliminato")

# ================= LIST COMMANDS =================
async def listcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT command FROM custom_commands")
    rows = cursor.fetchall()

    text = "\n".join([f"/{r[0]}" for r in rows]) or "Nessun comando"

    await update.message.reply_text(f"📜 Comandi:\n{text}")

# ================= BUTTON HANDLER =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "back":
        await query.message.edit_text("🏠 Menu", reply_markup=main_menu())
        return

    # ✅ FIX IMPORTANTE
    if data.startswith("cmd:"):
        cmd = data.split(":")[1].strip().lower()

        cursor.execute(
            "SELECT response FROM custom_commands WHERE LOWER(command)=LOWER(%s) LIMIT 1",
            (cmd,)
        )
        result = cursor.fetchone()

        if result:
            await query.message.reply_text(result[0])
        else:
            await query.message.reply_text("❌ Comando non trovato")

    elif data == "canali":
        await canali(update, context)

    elif data == "contatti":
        await contatti(update, context)

# ================= MESSAGE HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    cursor.execute(
        "SELECT response FROM custom_commands WHERE LOWER(command)=LOWER(%s) LIMIT 1",
        (text,)
    )
    result = cursor.fetchone()

    if result:
        await update.message.reply_text(result[0])

# ================= SET COMMANDS =================
async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Avvia il bot"),
        BotCommand("canali", "I nostri canali"),
        BotCommand("contatti", "Contatti"),
        BotCommand("admin", "Admin")
    ])

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.post_init = set_commands

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CommandHandler("addcmd", addcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))
    app.add_handler(CommandHandler("listcmd", listcmd))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE PERFETTO")
    app.run_polling()

if __name__ == "__main__":
    main()
