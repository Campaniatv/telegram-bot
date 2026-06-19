import os
import psycopg2
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN mancante nelle variabili di ambiente.")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante nelle variabili di ambiente.")

# ================= DATABASE =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS custom_commands (
    command TEXT PRIMARY KEY,
    text TEXT NOT NULL
)
""")

conn.commit()

def db_touch_user(user_id: int):
    cursor.execute("""
    INSERT INTO users (user_id, last_active)
    VALUES (%s, CURRENT_TIMESTAMP)
    ON CONFLICT (user_id) DO UPDATE SET last_active=CURRENT_TIMESTAMP
    """, (user_id,))
    conn.commit()

def db_get_custom_text(cmd: str):
    cursor.execute("SELECT text FROM custom_commands WHERE command=%s", (cmd,))
    row = cursor.fetchone()
    return row[0] if row else None

def db_set_custom_text(cmd: str, text: str):
    cursor.execute("""
    INSERT INTO custom_commands (command, text)
    VALUES (%s, %s)
    ON CONFLICT (command) DO UPDATE SET text=EXCLUDED.text
    """, (cmd, text))
    conn.commit()

def db_del_custom_text(cmd: str):
    cursor.execute("DELETE FROM custom_commands WHERE command=%s", (cmd,))
    conn.commit()

def db_count_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

def db_count_today_users():
    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active::date = CURRENT_DATE
    """)
    return cursor.fetchone()[0]

def db_count_month_users():
    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active >= date_trunc('month', CURRENT_DATE)
    """)
    return cursor.fetchone()[0]

def db_fetch_all_user_ids():
    cursor.execute("SELECT user_id FROM users")
    return [r[0] for r in cursor.fetchall()]

def is_blocked_error(e) -> bool:
    # Gestiamo i casi tipici: forbidden/blocked/user deactivated
    msg = str(e).lower()
    return ("forbidden" in msg) or ("blocked" in msg) or ("bot was blocked" in msg) or ("user is deactivated" in msg)

# ================= STATI =================
# user_state: { user_id: "addcmd_name" | "addcmd_text" | "delcmd" | "broadcast" | None }
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

# ================= UTIL =================
async def safe_edit_text(query, text, reply_markup=None, parse_mode=None):
    try:
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        # Se edit fallisce (es. stesso testo), prova a inviare invece di editare
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

async def set_bot_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Avvia bot"),
        BotCommand("canali", "Vedi canali"),
        BotCommand("contatti", "Contatti"),
        BotCommand("admin", "Pannello admin")
    ])

# ================= START COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_touch_user(user_id)

    await update.message.reply_text(
        "🏠 *Benvenuto nel bot!*",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= CANALI COMMAND =================
async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_touch_user(update.effective_user.id)

    await update.message.reply_text(
        "📢 *I nostri canali:*",
        reply_markup=canali_menu(),
        parse_mode="Markdown"
    )

# ================= CONTATTI COMMAND =================
async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_touch_user(update.effective_user.id)

    await update.message.reply_text(
        "📞 *Contatti:*",
        reply_markup=contatti_menu(),
        parse_mode="Markdown"
    )

# ================= ADMIN COMMAND =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    await update.message.reply_text(
        "🔧 *Pannello Admin*",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )

# ================= CALLBACK BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "canali":
        await safe_edit_text(
            query,
            "📢 *Scegli un canale:*",
            reply_markup=canali_menu(),
            parse_mode="Markdown"
        )

    elif data == "contatti":
        await safe_edit_text(
            query,
            "📞 *Contatti:*",
            reply_markup=contatti_menu(),
            parse_mode="Markdown"
        )

    elif data == "back":
        if user_id == ADMIN_ID:
            await safe_edit_text(query, "🔧 *Pannello Admin*", reply_markup=admin_menu(), parse_mode="Markdown")
        else:
            await safe_edit_text(query, "🏠 *Menu principale*", reply_markup=main_menu(), parse_mode="Markdown")

    elif data == "stats":
        if user_id != ADMIN_ID:
            return
        total = db_count_users()
        today = db_count_today_users()
        month = db_count_month_users()

        await safe_edit_text(
            query,
            f"📊 *Statistiche*\n\n👥 Totali: {total}\n📅 Oggi: {today}\n🗓 Mese: {month}",
            reply_markup=admin_menu(),
            parse_mode="Markdown"
        )

    elif data == "broadcast":
        if user_id != ADMIN_ID:
            return
        user_state[user_id] = "broadcast"
        await query.message.reply_text("📢 Invia ora il *messaggio* da broadcast (testo).")

    elif data == "addcmd":
        if user_id != ADMIN_ID:
            return
        user_state[user_id] = "addcmd_name"
        await query.message.reply_text("➕ Scrivi il *nome comando* (senza /). Esempio: `pippo`")

    elif data == "delcmd":
        if user_id != ADMIN_ID:
            return
        user_state[user_id] = "delcmd"
        await query.message.reply_text("❌ Scrivi il *nome comando* da eliminare (senza /).")

# ================= MESSAGE HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_touch_user(user_id)

    # deve essere testo per i nostri stati (add/del/broadcast)
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # ===== ADD CMD NAME =====
    if user_state.get(user_id) == "addcmd_name":
        cmd = text.lower().lstrip("/")
        if not cmd:
            await update.message.reply_text("❌ Nome comando non valido.")
            user_state[user_id] = None
            return

        temp_data[user_id] = cmd
        user_state[user_id] = "addcmd_text"
        await update.message.reply_text("📝 Ora scrivi *il testo* che deve rispondere al comando /" + cmd, parse_mode="Markdown")
        return

    # ===== ADD CMD TEXT =====
    if user_state.get(user_id) == "addcmd_text":
        cmd = temp_data.get(user_id)
        if not cmd:
            user_state[user_id] = None
            return

        db_set_custom_text(cmd, text)
        user_state[user_id] = None
        temp_data.pop(user_id, None)

        await update.message.reply_text(f"✅ Comando /{cmd} salvato.", parse_mode="Markdown")
        return

    # ===== DELETE CMD =====
    if user_state.get(user_id) == "delcmd":
        cmd = text.lower().lstrip("/")
        if not cmd:
            await update.message.reply_text("❌ Nome comando non valido.")
            user_state[user_id] = None
            return

        db_del_custom_text(cmd)
        user_state[user_id] = None
        await update.message.reply_text(f"❌ Comando /{cmd} eliminato.", parse_mode="Markdown")
        return

    # ===== BROADCAST =====
    if user_state.get(user_id) == "broadcast":
        if user_id != ADMIN_ID:
            user_state[user_id] = None
            return

        # broadcast SOLO testo
        all_ids = db_fetch_all_user_ids()

        sent = 0
        removed = 0

        for uid in all_ids:
            try:
                await context.bot.send_message(uid, text)
                sent += 1
            except Exception as e:
                if is_blocked_error(e):
                    cursor.execute("DELETE FROM users WHERE user_id=%s", (uid,))
                    conn.commit()
                    removed += 1
                else:
                    # Non rimuoviamo altri utenti se errore generico
                    pass

        user_state[user_id] = None
        await update.message.reply_text(f"✅ Broadcast completato!\n📨 Inviati: {sent}\n🚫 Rimossi (bloccano): {removed}")
        return

    # ===== CUSTOM COMMAND ANSWER =====
    # Risponde SOLO ai messaggi che iniziano con "/nome"
    if text.startswith("/"):
        cmd = text.split()[0].replace("/", "").lower()
        reply_text = db_get_custom_text(cmd)
        if reply_text:
            await update.message.reply_text(reply_text)

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    # imposta comandi visibili in Telegram
    app.post_init = set_bot_commands

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(buttons))
    # gestiamo tutti i messaggi testuali non-comando
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ BOT PRO ONLINE (PRO).")
    app.run_polling()

if __name__ == "__main__":
    main()
