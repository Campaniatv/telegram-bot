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

cursor.execute("""
CREATE TABLE IF NOT EXISTS custom_commands (
    command TEXT PRIMARY KEY,
    response TEXT
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
broadcast_data = {}

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Crea comando", callback_data="newcmd")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("SELECT last_active FROM users WHERE user_id = %s", (user.id,))
    data = cursor.fetchone()

    now = datetime.utcnow()

    if data:
        last_active = data[0]
        if last_active and (now - last_active) > timedelta(days=2):
            text = "👋 Bentornato!\n✅ Bot attivo"
        else:
            text = "✅ Bot già attivo!"
    else:
        text = "👋 Benvenuto!\n✅ Bot attivo!"

    add_user(user)
    update_active(user.id)

    await update.message.reply_text(text, reply_markup=main_menu())

# ================= INFO =================
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ INFO\nRiceverai aggiornamenti e promozioni.",
        reply_markup=back_button()
    )

# ================= CANALI =================
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 CANALI",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Film / Serie", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
        ])
    )

# ================= CONTATTI =================
async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Contatti\nTelegram: https://t.me/CAMPANIAVIP",
        reply_markup=back_button()
    )

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🔧 Admin",
        reply_markup=admin_menu()
    )

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_state[update.effective_user.id] = "broadcast_msg"
    await update.message.reply_text("📢 Invia il messaggio")

# ================= CREA COMANDO =================
async def setcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Uso: /setcmd nome")
        return

    cmd = context.args[0].lower()
    user_state[update.effective_user.id] = f"setcmd_{cmd}"

    await update.message.reply_text(f"✍️ Invia testo per /{cmd}")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "back":
        if user_id == ADMIN_ID:
            await query.message.edit_text("🔧 Admin", reply_markup=admin_menu())
        else:
            await query.message.edit_text("🏠 Menu", reply_markup=main_menu())

    elif query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_DATE")
        today = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE DATE_TRUNC('month', joined_at) = DATE_TRUNC('month', CURRENT_DATE)
        """)
        month = cursor.fetchone()[0]

        await query.message.reply_text(
            f"👥 Totali: {total}\n📅 Oggi: {today}\n🗓 Mese: {month}"
        )

    elif query.data == "broadcast":
        user_state[user_id] = "broadcast_msg"
        await query.message.reply_text("📢 Invia messaggio")

    elif query.data == "newcmd":
        user_state[user_id] = "waiting_cmd"
        await query.message.reply_text("✍️ Scrivi nome comando (es: promo)")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_active(user_id)

    text = update.message.text

    # ✅ COMANDI PERSONALIZZATI
    if text and text.startswith("/"):
        cmd = text[1:].split()[0]
        cursor.execute("SELECT response FROM custom_commands WHERE command = %s", (cmd,))
        res = cursor.fetchone()
        if res:
            await update.message.reply_text(res[0])
            return

    state = user_state.get(user_id)

    # ✅ CREA COMANDO
    if state == "waiting_cmd":
        user_state[user_id] = f"setcmd_{text}"
        await update.message.reply_text("✅ Ora invia il testo")
        return

    if state and state.startswith("setcmd_"):
        cmd = state.replace("setcmd_", "")
        cursor.execute("""
        INSERT INTO custom_commands (command, response)
        VALUES (%s, %s)
        ON CONFLICT (command) DO UPDATE SET response = EXCLUDED.response
        """, (cmd, text))
        conn.commit()

        user_state[user_id] = None
        await update.message.reply_text(f"✅ Comando /{cmd} salvato!")
        return

    # ✅ BROADCAST STEP 1
    if state == "broadcast_msg":
        broadcast_data[user_id] = update.message
        user_state[user_id] = "broadcast_buttons"

        await update.message.reply_text(
            "➕ Invia bottoni oppure scrivi skip\nFormato:\nNome - link"
        )
        return

    # ✅ BROADCAST STEP 2
    if state == "broadcast_buttons":
        buttons = []

        if text.lower() != "skip":
            for line in text.split("\n"):
                if " - " in line:
                    name, url = line.split(" - ", 1)
                    buttons.append([InlineKeyboardButton(name, url=url)])

        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0

        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=broadcast_data[user_id].chat_id,
                    message_id=broadcast_data[user_id].message_id,
                    reply_markup=keyboard
                )
                sent += 1
                await asyncio.sleep(0.05)
            except:
                removed += 1

        user_state[user_id] = None

        await update.message.reply_text(
            f"✅ Broadcast completato!\n📤 Inviati: {sent}\n🚫 Errori: {removed}"
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("setcmd", setcmd))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
