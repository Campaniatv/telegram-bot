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
    response TEXT,
    buttons TEXT
)
""")

conn.commit()

# ================= CACHE =================
user_state = {}
temp_cmd = {}
temp_text = {}

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
    cursor.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id=%s", (user_id,))
    conn.commit()

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
        [InlineKeyboardButton("➕ Comando", callback_data="addcmd")],
        [InlineKeyboardButton("🗑️ Elimina comando", callback_data="delcmd")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)
    update_active(user.id)

    await update.message.reply_text(
        "👋 Benvenuto!\n\nUsa i pulsanti sotto 👇",
        reply_markup=main_menu()
    )

# ================= COMANDI BASE =================
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 https://t.me/AggiornamentiCampaniabot")

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📞 https://t.me/CAMPANIAVIP")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🔧 Pannello Admin",
        reply_markup=admin_menu()
    )

# ================= COMANDI CUSTOM =================
async def setcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Uso: /setcmd nome")
        return

    cmd = context.args[0].lower()
    temp_cmd[update.effective_user.id] = cmd
    user_state[update.effective_user.id] = "cmd_text"

    await update.message.reply_text(f"Inserisci testo per /{cmd}")

async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Uso: /delcmd nome")
        return

    cmd = context.args[0].lower()
    cursor.execute("DELETE FROM custom_commands WHERE command=%s", (cmd,))
    conn.commit()

    await update.message.reply_text(f"✅ /{cmd} eliminato")

# ================= CALLBACK =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    if query.data == "canali":
        await query.message.edit_text(
            "📢 https://t.me/AggiornamentiCampaniabot",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]])
        )

    elif query.data == "contatti":
        await query.message.edit_text(
            "📞 https://t.me/CAMPANIAVIP",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]])
        )

    elif query.data == "back":
        if uid == ADMIN_ID:
            await query.message.edit_text("🔧 Admin", reply_markup=admin_menu())
        else:
            await query.message.edit_text("🏠 Menu", reply_markup=main_menu())

    elif query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_DATE")
        today = cursor.fetchone()[0]

        await query.message.reply_text(f"👥 Totali: {total}\n📅 Oggi: {today}")

    elif query.data == "broadcast":
        user_state[uid] = "broadcast"
        await query.message.reply_text("Invia messaggio broadcast")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_active(uid)

    state = user_state.get(uid)

    # ===== CREA COMANDO =====
    if state == "cmd_text":
        temp_text[uid] = update.message.text
        user_state[uid] = "cmd_buttons"
        await update.message.reply_text("Bottoni? (Nome - link) oppure skip")
        return

    if state == "cmd_buttons":
        buttons = update.message.text if update.message.text.lower() != "skip" else ""

        cursor.execute("""
        INSERT INTO custom_commands (command, response, buttons)
        VALUES (%s,%s,%s)
        ON CONFLICT (command) DO UPDATE SET
        response=EXCLUDED.response,
        buttons=EXCLUDED.buttons
        """, (temp_cmd[uid], temp_text[uid], buttons))

        conn.commit()
        user_state[uid] = None

        await update.message.reply_text("✅ Comando salvato")
        return

    # ===== BROADCAST =====
    if state == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0
        errors = 0

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
                err = str(e).lower()

                # ✅ SOLO BLOCCATI
                if "blocked" in err or "forbidden" in err:
                    cursor.execute("DELETE FROM users WHERE user_id=%s", (u,))
                    conn.commit()
                    removed += 1
                else:
                    errors += 1

        user_state[uid] = None

        await update.message.reply_text(
            f"✅ Inviati: {sent}\n🚫 Bloccato: {removed}\n⚠️ Errori: {errors}"
        )
        return

    # ===== COMANDI CUSTOM =====
    if update.message.text and update.message.text.startswith("/"):
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
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("setcmd", setcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("🔥 BOT PRO ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
