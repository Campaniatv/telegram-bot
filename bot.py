import os
import psycopg2
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from telegram.error import Forbidden

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
CREATE TABLE IF NOT EXISTS commands (
    name TEXT PRIMARY KEY,
    response TEXT
)
""")

conn.commit()

# ================= STATE =================
user_state = {}

# ================= UTENTI =================
def add_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=%s",(user_id,))
    if cursor.fetchone():
        return False
    cursor.execute("INSERT INTO users (user_id) VALUES (%s)",(user_id,))
    conn.commit()
    return True

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Promo Esclusive", callback_data="promo")],
        [InlineKeyboardButton("📢 Canali Ufficiali", callback_data="canali")],
        [InlineKeyboardButton("📞 Assistenza", callback_data="contatti")],
        [InlineKeyboardButton("📱 Scarica App", callback_data="app")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new = add_user(user_id)

    if new:
        text = "✅ *Benvenuto!*\n\n🚀 Il bot è ora attivo.\nScopri subito tutte le funzionalità 👇"
    else:
        text = "⚡ *Bentornato!*\n\nIl bot è già attivo ✅"

    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

# ================= COMANDI =================
async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *PROMO ESCLUSIVE*\n\n"
        "🎬 Film, Serie e Sport senza limiti\n"
        "⚡ Accesso immediato\n"
        "💎 Qualità top\n\n"
        "👉 Non perdere le offerte attive!",
        parse_mode="Markdown"
    )

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *ASSISTENZA*\n\n"
        "💬 Telegram: https://t.me/CAMPANIAVIP\n"
        "📲 WhatsApp: https://wa.me/+393509741712\n\n"
        "⚡ Risposta veloce garantita",
        parse_mode="Markdown"
    )

async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
        [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")]
    ]
    await update.message.reply_text(
        "📢 *CANALI UFFICIALI*\n\nScegli dove entrare 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def app_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *APP IN ARRIVO*\n\n🚀 Stiamo preparando qualcosa di grosso...\nResta aggiornato!",
        parse_mode="Markdown"
    )

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "promo":
        await promo(update, context)
    elif q.data == "canali":
        await canali(update, context)
    elif q.data == "contatti":
        await contatti(update, context)
    elif q.data == "app":
        await app_cmd(update, context)

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    await update.message.reply_text("👑 *PANNELLO ADMIN*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ================= CALLBACK ADMIN =================
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if update.effective_user.id != ADMIN_ID:
        return

    if q.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        today = datetime.now().date()
        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at)=%s",(today,))
        today_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE_TRUNC('month', joined_at)=DATE_TRUNC('month', CURRENT_DATE)")
        month_count = cursor.fetchone()[0]

        await q.edit_message_text(
            f"📊 *STATISTICHE*\n\n👥 Totali: {total}\n🔥 Oggi: {today_count}\n📆 Mese: {month_count}",
            parse_mode="Markdown"
        )

    elif q.data == "broadcast":
        user_state[ADMIN_ID] = "broadcast"
        await q.edit_message_text("📢 Invia ora *testo, foto o video* da mandare a tutti", parse_mode="Markdown")

# ================= BROADCAST =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # BROADCAST
    if user_state.get(user_id) == "broadcast":
        user_state[user_id] = None

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        removed = 0

        for (uid,) in users:
            try:
                if update.message.text:
                    await context.bot.send_message(uid, update.message.text)
                elif update.message.photo:
                    await context.bot.send_photo(uid, update.message.photo[-1].file_id, caption=update.message.caption)
                elif update.message.video:
                    await context.bot.send_video(uid, update.message.video.file_id, caption=update.message.caption)

                sent += 1

            except Forbidden:
                cursor.execute("DELETE FROM users WHERE user_id=%s",(uid,))
                conn.commit()
                removed += 1

        await update.message.reply_text(f"✅ Inviati: {sent}\n❌ Rimossi: {removed}")
        return

    # CUSTOM COMMANDS
    text = update.message.text.lower()

    cursor.execute("SELECT response FROM commands WHERE name=%s",(text,))
    res = cursor.fetchone()

    if res:
        await update.message.reply_text(res[0])

# ================= COMANDI CUSTOM =================
async def listcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT name FROM commands")
    cmds = cursor.fetchall()

    if not cmds:
        await update.message.reply_text("❌ Nessun comando")
        return

    text = "\n".join([c[0] for c in cmds])
    await update.message.reply_text(f"📜 Comandi:\n\n{text}")

async def addcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        data = update.message.text.split(" ",1)[1]
        name, res = data.split("|",1)

        cursor.execute("INSERT INTO commands VALUES (%s,%s)",(name.lower(),res))
        conn.commit()

        await update.message.reply_text("✅ Comando aggiunto")
    except:
        await update.message.reply_text("uso: /addcmd nome|testo")

async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        name = update.message.text.split(" ",1)[1]

        cursor.execute("DELETE FROM commands WHERE name=%s",(name.lower(),))
        conn.commit()

        await update.message.reply_text("✅ Comando eliminato")
    except:
        await update.message.reply_text("uso: /delcmd nome")

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("app", app_cmd))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("listcmd", listcmd))
    app.add_handler(CommandHandler("addcmd", addcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(CallbackQueryHandler(admin_buttons))

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE LIVELLO PRO")
    app.run_polling()

if __name__ == "__main__":
    main()
