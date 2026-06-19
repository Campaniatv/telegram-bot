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
    text TEXT
)
""")

conn.commit()

# ================= STATI =================
user_state = {}
temp_data = {}

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
        [InlineKeyboardButton("➕ Aggiungi comando", callback_data="addcmd")],
        [InlineKeyboardButton("❌ Elimina comando", callback_data="delcmd")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

def canali_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Film, Serie & Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
        [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

def contatti_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Telegram", url="https://t.me/CAMPANIAVIP")],
        [InlineKeyboardButton("📱 WhatsApp", url="https://wa.me/393509741712")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
        conn.commit()

    await update.message.reply_text(
        "🏠 *Benvenuto nel bot!*",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= COMANDI =================
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 *I nostri canali:*", reply_markup=canali_menu(), parse_mode="Markdown")

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📞 *Contatti:*", reply_markup=contatti_menu(), parse_mode="Markdown")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text("🔧 *Pannello Admin*", reply_markup=admin_menu(), parse_mode="Markdown")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "canali":
        await query.message.edit_text("📢 *Scegli un canale:*", reply_markup=canali_menu(), parse_mode="Markdown")

    elif query.data == "contatti":
        await query.message.edit_text("📞 *Contatti:*", reply_markup=contatti_menu(), parse_mode="Markdown")

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
        await query.message.edit_text(f"👥 Utenti totali: {total}", reply_markup=admin_menu())

    elif query.data == "broadcast":
        user_state[user_id] = "broadcast"
        await query.message.reply_text("📢 Invia il messaggio da inviare a tutti")

    elif query.data == "addcmd":
        user_state[user_id] = "addcmd_name"
        await query.message.reply_text("✏️ Scrivi il nome comando (senza /)")

    elif query.data == "delcmd":
        user_state[user_id] = "delcmd"
        await query.message.reply_text("❌ Scrivi il comando da eliminare")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # ===== ADD CMD =====
    if user_state.get(user_id) == "addcmd_name":
        temp_data[user_id] = text.lower()
        user_state[user_id] = "addcmd_text"
        await update.message.reply_text("📝 Ora scrivi il testo del comando")
        return

    elif user_state.get(user_id) == "addcmd_text":
        cmd = temp_data[user_id]
        cursor.execute(
            "INSERT INTO custom_commands VALUES (%s,%s) ON CONFLICT (command) DO UPDATE SET text=%s",
            (cmd, text, text)
        )
        conn.commit()
        user_state[user_id] = None
        await update.message.reply_text(f"✅ Comando /{cmd} salvato")
        return

    # ===== DELETE CMD =====
    elif user_state.get(user_id) == "delcmd":
        cursor.execute("DELETE FROM custom_commands WHERE command=%s", (text.lower(),))
        conn.commit()
        user_state[user_id] = None
        await update.message.reply_text("❌ Comando eliminato")
        return

    # ===== BROADCAST =====
    elif user_state.get(user_id) == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0

        for u in users:
            uid = u[0]
            try:
                await context.bot.send_message(uid, text)
                sent += 1
            except:
                cursor.execute("DELETE FROM users WHERE user_id=%s", (uid,))
                conn.commit()
                removed += 1

        user_state[user_id] = None
        await update.message.reply_text(f"✅ Inviati: {sent}\n🚫 Rimossi: {removed}")
        return

    # ===== CUSTOM CMD =====
    if text.startswith("/"):
        cmd = text.replace("/", "")
        cursor.execute("SELECT text FROM custom_commands WHERE command=%s", (cmd,))
        res = cursor.fetchone()
        if res:
            await update.message.reply_text(res[0])

# ================= COMANDI MENU =================
async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Avvia bot"),
        BotCommand("canali", "Vedi canali"),
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

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE PRO")
    app.run_polling()

if __name__ == "__main__":
    main()
