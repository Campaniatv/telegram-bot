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
        [InlineKeyboardButton("🔥 Promo", callback_data="promo")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("📱 App", callback_data="app")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new = add_user(user_id)

    if new:
        text = "✅ Bot attivo!"
    else:
        text = "⚡ Bot già attivo!"

    await update.message.reply_text(text, reply_markup=main_menu())

# ================= COMANDI =================
async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Promo disponibili presto")

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/+393509741712"
    )

async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
        [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")]
    ]
    await update.message.reply_text(
        "📢 CANALI UFFICIALI\n\nScegli:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def app_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 App in arrivo")

# ================= BOTTONI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "promo":
        await query.edit_message_text("🔥 Promo disponibili presto")

    elif query.data == "canali":
        keyboard = [
            [InlineKeyboardButton("🎬 Film / Serie / Sport", url="https://t.me/+HLygUda0f_wwNmE0")],
            [InlineKeyboardButton("⚽ Solo Sport", url="https://t.me/+Xv4kd5Uja0YzY2M0")]
        ]
        await query.edit_message_text(
            "📢 CANALI UFFICIALI\n\nScegli:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "contatti":
        await query.edit_message_text(
            "📞 CONTATTI:\n\n"
            "Telegram: https://t.me/CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/+393509741712"
        )

    elif query.data == "app":
        await query.edit_message_text("📱 App in arrivo")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    today = datetime.now().date()
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at)=%s",(today,))
    today_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE_TRUNC('month', joined_at)=DATE_TRUNC('month', CURRENT_DATE)")
    month_count = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👑 ADMIN\n\n"
        f"👥 Totali: {total}\n"
        f"📅 Oggi: {today_count}\n"
        f"📆 Mese: {month_count}"
    )

# ================= CUSTOM COMMAND =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    cursor.execute("SELECT response FROM commands WHERE name=%s",(text,))
    res = cursor.fetchone()

    if res:
        await update.message.reply_text(res[0])

# ================= LISTCMD =================
async def listcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT name FROM commands")
    cmds = cursor.fetchall()

    if not cmds:
        await update.message.reply_text("❌ Nessun comando")
        return

    text = "\n".join([c[0] for c in cmds])
    await update.message.reply_text(f"📜 Comandi:\n\n{text}")

# ================= ADDCMD =================
async def addcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        data = update.message.text.split(" ",1)[1]
        name, res = data.split("|",1)

        cursor.execute("INSERT INTO commands VALUES (%s,%s)",(name.lower(),res))
        conn.commit()

        await update.message.reply_text("✅ aggiunto")
    except:
        await update.message.reply_text("uso: /addcmd nome|testo")

# ================= DELCMD =================
async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        name = update.message.text.split(" ",1)[1]

        cursor.execute("DELETE FROM commands WHERE name=%s",(name.lower(),))
        conn.commit()

        await update.message.reply_text("✅ eliminato")
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
    app.add_handler(CommandHandler("listcmd", listcmd))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("addcmd", addcmd))
    app.add_handler(CommandHandler("delcmd", delcmd))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE PERFETTO")
    app.run_polling()

if __name__ == "__main__":
    main()
