import os
import sys
import atexit
import psycopg2

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN or not DATABASE_URL:
    print("❌ BOT_TOKEN o DATABASE_URL mancanti. Controlla Railway env vars.")
    sys.exit(1)

# ================= DATABASE (sync) =================
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cursor = conn.cursor()

# ================= INIT DB =================
def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_lock (
        id INTEGER PRIMARY KEY,
        active BOOLEAN NOT NULL DEFAULT FALSE,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    cursor.execute("""
    INSERT INTO bot_lock (id, active)
    VALUES (1, FALSE)
    ON CONFLICT (id) DO NOTHING
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        link TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'altro'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        value TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_commands (
        command TEXT PRIMARY KEY,
        response TEXT NOT NULL
    )
    """)

    # Tabelle per admin "pannello"
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    conn.commit()

def ensure_defaults():
    """
    Crea i dati base se non esistono.
    Puoi poi cambiarli con le insert SQL o con comandi admin (se vuoi li aggiungiamo).
    """
    # canali di default
    cursor.execute("SELECT COUNT(*) FROM channels")
    n = cursor.fetchone()[0]
    if n == 0:
        # ESEMPIO: metti qui i tuoi link reali
        cursor.execute("""
            INSERT INTO channels (title, link, category) VALUES
            ('🎬 Film & Serie', 'https://t.me/SEUO_FILM_SERIE', 'film'),
            ('🏀 Sport', 'https://t.me/SEUO_SPORT', 'sport')
        """)
        conn.commit()

    # contatti di default
    cursor.execute("SELECT COUNT(*) FROM contacts")
    n = cursor.fetchone()[0]
    if n == 0:
        # ESEMPIO: metti qui numero/contatto reali
        # value: per WhatsApp usa numero con + (es: +39350....)
        cursor.execute("""
            INSERT INTO contacts (title, value) VALUES
            ('WhatsApp', '+393509741712'),
            ('Telegram', '@IL_TUO_USERNAME_TELEGRAM')
        """)
        conn.commit()

    # custom commands di default
    cursor.execute("SELECT COUNT(*) FROM custom_commands")
    n = cursor.fetchone()[0]
    if n == 0:
        cursor.execute("""
            INSERT INTO custom_commands (command, response) VALUES
            ('salve', 'Ciao! Usa i pulsanti per vedere canali e contatti 👇'),
            ('film', 'Vai alla sezione 🎬 Film & Serie nel menu.'),
            ('sport', 'Vai alla sezione 🏀 Sport nel menu.')
        """)
        conn.commit()

# ================= ANTI-DUPLICATO BOT (lock DB) =================
def acquire_lock():
    """
    Se il lock risulta già active, blocca l’avvio.
    """
    cursor.execute("SELECT active FROM bot_lock WHERE id=1")
    row = cursor.fetchone()
    active = bool(row[0]) if row else False

    if active:
        print("❌ BOT GIÀ ATTIVO (lock DB active) - STOP")
        return False

    cursor.execute("""
        UPDATE bot_lock SET active=TRUE, updated_at=NOW() WHERE id=1
    """)
    conn.commit()
    print("✅ Lock acquisito (anti-duplicato attivo)")
    return True

def release_lock():
    try:
        cursor.execute("UPDATE bot_lock SET active=FALSE, updated_at=NOW() WHERE id=1")
        conn.commit()
        print("🔓 Lock rilasciato")
    except:
        pass

# release anche se chiudi processo
atexit.register(release_lock)

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Canali", callback_data="cmd:canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="cmd:contatti")],
        [InlineKeyboardButton("🛠️ Admin", callback_data="cmd:admin")],
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Indietro", callback_data="back:main")]
    ])

# ================= DB HELPERS =================
def add_user(user_id: int):
    cursor.execute("""
        INSERT INTO users (user_id) VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id,))
    conn.commit()

def get_custom_response(text: str):
    t = text.strip().lower()
    cursor.execute("""
        SELECT response FROM custom_commands
        WHERE LOWER(command)=LOWER(%s)
        LIMIT 1
    """, (t,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_channels():
    cursor.execute("""
        SELECT title, link, category
        FROM channels
        ORDER BY category, title
    """)
    return cursor.fetchall()

def get_contacts():
    cursor.execute("""
        SELECT title, value
        FROM contacts
        ORDER BY title
    """)
    return cursor.fetchall()

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    await update.message.reply_text(
        "🔥 Benvenuto! Scegli dal menu 👇",
        reply_markup=main_menu()
    )

async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_channels()
    if not rows:
        await update.message.reply_text("Nessun canale nel DB. Admin aggiorna i link.")
        return

    # raggruppa
    film = []
    sport = []
    altro = []

    for title, link, category in rows:
        item = f"• {title}\n  {link}"
        cat = (category or "").lower()
        if "film" in cat:
            film.append(item)
        elif "sport" in cat:
            sport.append(item)
        else:
            altro.append(item)

    msg_parts = []
    if film:
        msg_parts.append("🎬 <b>Film & Serie</b>\n" + "\n\n".join(film))
    if sport:
        msg_parts.append("🏀 <b>Sport</b>\n" + "\n\n".join(sport))
    if altro:
        msg_parts.append("📌 <b>Altro</b>\n" + "\n\n".join(altro))

    await update.message.reply_text(
        "\n\n".join(msg_parts),
        parse_mode="HTML",
        reply_markup=back_menu()
    )

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_contacts()
    if not rows:
        await update.message.reply_text("Nessun contatto nel DB. Admin aggiorna i valori.")
        return

    wa = None
    tg = None
    other = []

    for title, value in rows:
        if title.lower().startswith("whatsapp"):
            wa = value
        elif title.lower().startswith("telegram"):
            tg = value
        else:
            other.append(f"• {title}: {value}")

    kb = []
    text_lines = ["📞 <b>Contatti</b>"]

    # WhatsApp
    if wa:
        wa_clean = wa.replace(" ", "")
        wa_link = f"https://wa.me/{wa_clean.lstrip('+')}"
        kb.append([InlineKeyboardButton("💬 WhatsApp", url=wa_link)])
        text_lines.append(f"• WhatsApp: {wa}")

    # Telegram
    if tg:
        kb.append([InlineKeyboardButton("📨 Telegram", url=f"https://t.me/{tg.lstrip('@')}")])
        text_lines.append(f"• Telegram: {tg}")

    if other:
        text_lines.append("")
        text_lines.extend(other)

    if not kb:
        kb.append([InlineKeyboardButton("🔙 Indietro", callback_data="back:main")])

    reply_markup = InlineKeyboardMarkup(kb + [[InlineKeyboardButton("🔙 Indietro", callback_data="back:main")]])

    await update.message.reply_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato.")
        return

    await update.message.reply_text(
        "🛠️ <b>Pannello Admin</b>\n\n"
        "Usa questi comandi:\n"
        "• /addcmd <command> <risposta>\n"
        "• /delcmd <command>\n"
        "• /listcmd\n\n"
        "E vai con i pulsanti per vedere menu base.",
        parse_mode="HTML",
        reply_markup=back_menu()
    )

async def addcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /addcmd <command> <risposta>")
        return

    command = context.args[0].strip().lower()
    response = " ".join(context.args[1:]).strip()

    cursor.execute("""
        INSERT INTO custom_commands (command, response)
        VALUES (%s, %s)
        ON CONFLICT (command) DO UPDATE SET response=EXCLUDED.response
    """, (command, response))
    conn.commit()

    await update.message.reply_text(f"✅ Comando '{command}' aggiornato/aggiunto.")

async def delcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Uso: /delcmd <command>")
        return

    command = context.args[0].strip().lower()
    cursor.execute("DELETE FROM custom_commands WHERE LOWER(command)=LOWER(%s)", (command,))
    conn.commit()

    await update.message.reply_text(f"🗑️ Comando '{command}' rimosso (se esisteva).")

async def listcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Non autorizzato.")
        return

    cursor.execute("SELECT command, response FROM custom_commands ORDER BY command LIMIT 50")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Nessun comando custom nel DB.")
        return

    lines = ["📋 <b>Comandi custom</b> (max 50):"]
    for cmd, resp in rows:
        lines.append(f"• <code>{cmd}</code> → {resp[:60]}{'...' if len(resp) > 60 else ''}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = (query.data or "").strip()

    if data == "back:main":
        await query.edit_message_text("🔥 Menu principale:", reply_markup=main_menu())
        return

    if data == "cmd:canali":
        # usa funzione canali “in modo manuale” perché è callback
        rows = get_channels()
        if not rows:
            await query.edit_message_text("Nessun canale nel DB.")
            return

        film = []
        sport = []
        altro = []

        for title, link, category in rows:
            item = f"• {title}\n  {link}"
            cat = (category or "").lower()
            if "film" in cat:
                film.append(item)
            elif "sport" in cat:
                sport.append(item)
            else:
                altro.append(item)

        msg_parts = []
        if film:
            msg_parts.append("🎬 <b>Film & Serie</b>\n" + "\n\n".join(film))
        if sport:
            msg_parts.append("🏀 <b>Sport</b>\n" + "\n\n".join(sport))
        if altro:
            msg_parts.append("📌 <b>Altro</b>\n" + "\n\n".join(altro))

        await query.edit_message_text(
            "\n\n".join(msg_parts),
            parse_mode="HTML",
            reply_markup=back_menu()
        )
        return

    if data == "cmd:contatti":
        rows = get_contacts()
        if not rows:
            await query.edit_message_text("Nessun contatto nel DB.")
            return

        wa = None
        tg = None
        other = []

        for title, value in rows:
            if title.lower().startswith("whatsapp"):
                wa = value
            elif title.lower().startswith("telegram"):
                tg = value
            else:
                other.append(f"• {title}: {value}")

        text_lines = ["📞 <b>Contatti</b>"]
        kb = []

        if wa:
            wa_clean = wa.replace(" ", "")
            wa_link = f"https://wa.me/{wa_clean.lstrip('+')}"
            kb.append([InlineKeyboardButton("💬 WhatsApp", url=wa_link)])
            text_lines.append(f"• WhatsApp: {wa}")

        if tg:
            kb.append([InlineKeyboardButton("📨 Telegram", url=f"https://t.me/{tg.lstrip('@')}")])
            text_lines.append(f"• Telegram: {tg}")

        if other:
            text_lines.append("")
            text_lines.extend(other)

        if not kb:
            kb.append([InlineKeyboardButton("🔙 Indietro", callback_data="back:main")])

        kb.append([InlineKeyboardButton("🔙 Indietro", callback_data="back:main")])

        await query.edit_message_text(
            "\n".join(text_lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if data == "cmd:admin":
        if query.from_user.id != ADMIN_ID:
            await query.edit_message_text("⛔ Non autorizzato.")
            return
        await query.edit_message_text(
            "🛠️ <b>Pannello Admin</b>\n\n"
            "Usa:\n"
            "• /addcmd <command> <risposta>\n"
            "• /delcmd <command>\n"
            "• /listcmd\n\n"
            "Poi prova scrivendo il command in chat.",
            parse_mode="HTML",
            reply_markup=back_menu()
        )
        return

    await query.edit_message_text("Comando non riconosciuto.", reply_markup=main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    # Se è un command custom (es: "salve", "film", ecc.)
    resp = get_custom_response(text)
    if resp:
        await update.message.reply_text(resp, reply_markup=main_menu())
        return

    # fallback
    await update.message.reply_text(
        "Non ho trovato quel comando.\nProva:\n• salve\n• film\n• sport\n\nOppure usa i pulsanti 👇",
        reply_markup=main_menu()
    )

# ================= SET COMMANDS =================
async def set_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Avvia il bot"),
        BotCommand("canali", "I canali disponibili"),
        BotCommand("contatti", "Contatti WhatsApp/Telegram"),
        BotCommand("admin", "Pannello admin"),
        BotCommand("addcmd", "Aggiungi comando custom"),
        BotCommand("delcmd", "Elimina comando custom"),
        BotCommand("listcmd", "Lista comandi custom"),
    ])

# ================= MAIN =================
def main():
    init_db()
    ensure_defaults()

    if not acquire_lock():
        # non far partire polling
        sys.exit(0)

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ BOT ONLINE (anti-duplicato + menu + custom commands)")

    # anti-conflict updates: evita errori con getUpdates paralleli
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
