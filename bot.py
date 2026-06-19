import os
import asyncio
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters, CallbackContext
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DATABASE =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

def setup_database():
    # Tabella utenti esistente
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

    # Tabella per comandi personalizzati
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_commands (
        command_name TEXT PRIMARY KEY,
        response_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by BIGINT
    )
    """)

    # Tabella per broadcast inviati
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS broadcast_logs (
        id SERIAL PRIMARY KEY,
        admin_id BIGINT,
        message_type TEXT,
        message_content TEXT,
        sent_count INTEGER,
        failed_count INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

setup_database()

# ================= UTENTI =================
def add_user(user):
    cursor.execute("""
    INSERT INTO users (user_id, first_name, last_name, username)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (user_id) DO UPDATE SET
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        username = EXCLUDED.username,
        last_active = CURRENT_TIMESTAMP
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

# ================= COMANDI PRINCIPALI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)

    keyboard = [
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("🔧 Admin", callback_data="admin")]
    ]

    await update.message.reply_text(
        "👋 Benvenuto!\n\nScegli un'opzione:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ INFO\n\n"
        "In questo canale troverai comunicazioni ufficiali, aggiornamenti, avvisi e promozioni pubblicate periodicamente.\n\n"
        "Resta iscritto per non perdere nessuna novità."
    )

async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /canali"""
    keyboard = [
        [
            InlineKeyboardButton(
                "🎬 Film / Serie / Sport",
                url="https://t.me/+HLygUda0f_wwNmE0"
            )
        ],
        [
            InlineKeyboardButton(
                "⚽ Solo Sport",
                url="https://t.me/+Xv4kd5Uja0YzY2M0"
            )
        ]
    ]

    await update.message.reply_text(
        "📢 CANALI UFFICIALI\n\n"
        "🎬 Film, Serie TV e Sport\n"
        "⚽ Solo Sport\n\n"
        "Scegli il canale che preferisci:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /contatti"""
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: https://t.me/CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/393509741712"
    )

# ================= COMANDI ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /admin"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accesso negato. Solo l'amministratore può accedere.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Aggiungi Comando", callback_data="add_command")],
        [InlineKeyboardButton("➖ Elimina Comando", callback_data="remove_command")]
    ]

    await update.message.reply_text(
        "🔧 PANNELLO ADMIN",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def aggiungi_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /aggiungi_comando"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accesso negato.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Uso corretto: /aggiungi_comando [nome] [risposta]\n\n"
            "Esempio: `/aggiungi_comando promo Ciao a tutti! Offerta speciale!`"
        )
        return

    command_name = context.args[0].lower()
    response_text = " ".join(context.args[1:])

    try:
        cursor.execute("""
        INSERT INTO custom_commands (command_name, response_text, created_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (command_name) DO UPDATE SET
            response_text = EXCLUDED.response_text,
            created_by = EXCLUDED.created_by
        """, (command_name, response_text, update.effective_user.id))

        conn.commit()
        await update.message.reply_text(f"✅ Comando `/{command_name}` aggiunto/aggiornato con successo!")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {str(e)}")

async def elimina_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /elimina_comando"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accesso negato.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Uso corretto: /elimina_comando [nome]\n\n"
            "Esempio: `/elimina_comando promo`"
        )
        return

    command_name = context.args[0].lower()

    cursor.execute("DELETE FROM custom_commands WHERE command_name = %s", (command_name,))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ Comando `/{command_name}` eliminato con successo!")
    else:
        await update.message.reply_text(f"❌ Comando `/{command_name}` non trovato.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /broadcast migliorato"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accesso negato.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Uso corretto:\n"
            "/broadcast testo [messaggio] - Invia un messaggio di testo\n"
            "/broadcast foto [URL] [didascalia] - Invia una foto\n"
            "/broadcast video [URL] [didascalia] - Invia un video"
        )
        return

    broadcast_type = context.args[0].lower()

    if broadcast_type == "testo":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Devi fornire un messaggio di testo.")
            return

        message = " ".join(context.args[1:])
        user_state[update.effective_user.id] = ("broadcast_text", message)
        await update.message.reply_text("✅ Ora invia questo messaggio a tutti gli utenti.")

    elif broadcast_type == "foto":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Devi fornire l'URL della foto.")
            return

        photo_url = context.args[1]
        caption = " ".join(context.args[2:]) if len(context.args) > 2 else ""
        user_state[update.effective_user.id] = ("broadcast_photo", photo_url, caption)
        await update.message.reply_text("✅ Ora invia questa foto a tutti gli utenti.")

    elif broadcast_type == "video":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Devi fornire l'URL del video.")
            return

        video_url = context.args[1]
        caption = " ".join(context.args[2:]) if len(context.args) > 2 else ""
        user_state[update.effective_user.id] = ("broadcast_video", video_url, caption)
        await update.message.reply_text("✅ Ora invia questo video a tutti gli utenti.")

    else:
        await update.message.reply_text(
            "⚠️ Tipo di broadcast non valido. Usa:\n"
            "testo, foto o video"
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats"""
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active > NOW() - INTERVAL '1 day'
    """)
    today = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE last_active > NOW() - INTERVAL '30 days'
    """)
    month = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM custom_commands")
    custom_cmds = cursor.fetchone()[0]

    await update.message.reply_text(
        f"📊 STATISTICHE\n\n"
        f"👥 Utenti totali: {total}\n"
        f"🔥 Attivi oggi: {today}\n"
        f"📅 Attivi questo mese: {month}\n"
        f"➕ Comandi personalizzati: {custom_cmds}"
    )

# ================= GESTIONE PULSANTI =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await query.edit_message_text(
            "ℹ️ INFO\n\n"
            "In questo canale troverai comunicazioni ufficiali, aggiornamenti, avvisi e promozioni pubblicate periodicamente.\n\n"
            "Resta iscritto per non perdere nessuna novità."
        )

    elif query.data == "canali":
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎬 Film / Serie / Sport",
                    url="https://t.me/+HLygUda0f_wwNmE0"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚽ Solo Sport",
                    url="https://t.me/+Xv4kd5Uja0YzY2M0"
                )
            ]
        ]

        await query.edit_message_text(
            "📢 CANALI UFFICIALI\n\n"
            "🎬 Film, Serie TV e Sport\n"
            "⚽ Solo Sport\n\n"
            "Scegli il canale che preferisci:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "contatti":
        await query.edit_message_text(
            "📞 CONTATTI:\n\n"
            "Telegram: https://t.me/CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/393509741712"
        )

    elif query.data == "stats":
        if query.from_user.id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE last_active > NOW() - INTERVAL '1 day'
        """)
        today = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE last_active > NOW() - INTERVAL '30 days'
        """)
        month = cursor.fetchone()[0]

        await query.edit_message_text(
            f"📊 STATISTICHE\n\n"
            f"👥 Totali: {total}\n"
            f"🔥 Oggi: {today}\n"
            f"📅 Mese: {month}"
        )

    elif query.data == "broadcast":
        if query.from_user.id != ADMIN_ID:
            return

        user_state[query.from_user.id] = "broadcast_text"

        await query.edit_message_text(
            "📢 Invia il messaggio di testo da inviare a tutti gli utenti.\n\n"
            "Puoi anche inviare una foto o video con /broadcast foto o /broadcast video"
        )

    elif query.data == "add_command":
        if query.from_user.id != ADMIN_ID:
            return

        user_state[query.from_user.id] = "add_command"

        await query.edit_message_text(
            "➕ **Aggiungi Comando Personalizzato**\n\n"
            "Invia il comando nel formato:\n"
            "`/nuovo_comando risposta`\n\n"
            "Esempio: `/promo Ciao a tutti! Offerta speciale questa settimana!`"
        )

    elif query.data == "remove_command":
        if query.from_user.id != ADMIN_ID:
            return

        # Mostra i comandi esistenti per l'eliminazione
        cursor.execute("SELECT command_name FROM custom_commands")
        commands = cursor.fetchall()

        if not commands:
            await query.edit_message_text("❌ Non ci sono comandi personalizzati da eliminare.")
            return

        keyboard = [
            [InlineKeyboardButton(cmd[0], callback_data=f"remove_{cmd[0]}")]
            for cmd in commands
        ]
        keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="cancel")])

        await query.edit_message_text(
            "➖ **Elimina Comando Personalizzato**\n\n"
            "Seleziona un comando da eliminare:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("remove_"):
        if query.from_user.id != ADMIN_ID:
            return

        command_name = query.data[7:]

        cursor.execute("DELETE FROM custom_commands WHERE command_name = %s", (command_name,))
        conn.commit()

        await query.edit_message_text(f"✅ Comando `/{command_name}` eliminato con successo!")

    elif query.data == "cancel":
        await query.edit_message_text("❌ Operazione annullata.")

# ================= GESTIONE BROADCAST =================
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce l'invio dei broadcast"""
    user_id = update.effective_user.id

    if user_state.get(user_id) is None:
        return

    state = user_state[user_id]

    if state[0] == "broadcast_text":
        message = state[1]
        await send_broadcast_text(update, context, message)

    elif state[0] == "broadcast_photo":
        photo_url = state[1]
        caption = state[2] if len(state) > 2 else ""
        await send_broadcast_photo(update, context, photo_url, caption)

    elif state[0] == "broadcast_video":
        video_url = state[1]
        caption = state[2] if len(state) > 2 else ""
        await send_broadcast_video(update, context, video_url, caption)

    user_state[user_id] = None

async def send_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Invia un messaggio di testo a tutti gli utenti"""
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0
    failed = 0

    for (uid,) in users:
        try:
            await context.bot.send_message(chat_id=uid, text=message)
            sent += 1
            await asyncio.sleep(0.05)  # Anti-flood
        except Exception as e:
            logger.error(f"Errore nell'invio a {uid}: {e}")
            failed += 1
            # Rimuovi utente non valido
            try:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                conn.commit()
            except:
                pass

    # Log del broadcast
    cursor.execute("""
    INSERT INTO broadcast_logs (admin_id, message_type, message_content, sent_count, failed_count)
    VALUES (%s, %s, %s, %s, %s)
    """, (update.effective_user.id, "testo", message[:200], sent, failed))
    conn.commit()

    await update.message.reply_text(
        f"✅ Broadcast completato!\n"
        f"📤 Inviati: {sent}\n"
        f"❌ Falliti: {failed}"
    )

async def send_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, photo_url: str, caption: str = ""):
    """Invia una foto a tutti gli utenti"""
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0
    failed = 0

    for (uid,) in users:
        try:
            await context.bot.send_photo(chat_id=uid, photo=photo_url, caption=caption)
            sent += 1
            await asyncio.sleep(0.1)  # Anti-flood
        except Exception as e:
            logger.error(f"Errore nell'invio della foto a {uid}: {e}")
            failed += 1
            try:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                conn.commit()
            except:
                pass

    # Log del broadcast
    cursor.execute("""
    INSERT INTO broadcast_logs (admin_id, message_type, message_content, sent_count, failed_count)
    VALUES (%s, %s, %s, %s, %s)
    """, (update.effective_user.id, "foto", photo_url[:200], sent, failed))
    conn.commit()

    await update.message.reply_text(
        f"✅ Broadcast foto completato!\n"
        f"📤 Inviati: {sent}\n"
        f"❌ Falliti: {failed}"
    )

async def send_broadcast_video(update: Update, context: ContextTypes.DEFAULT_TYPE, video_url: str, caption: str = ""):
    """Invia un video a tutti gli utenti"""
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0
    failed = 0

    for (uid,) in users:
        try:
            await context.bot.send_video(chat_id=uid, video=video_url, caption=caption)
            sent += 1
            await asyncio.sleep(0.2)  # Anti-flood (video più pesanti)
        except Exception as e:
            logger.error(f"Errore nell'invio del video a {uid}: {e}")
            failed += 1
            try:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                conn.commit()
            except:
                pass

    # Log del broadcast
    cursor.execute("""
    INSERT INTO broadcast_logs (admin_id, message_type, message_content, sent_count, failed_count)
    VALUES (%s, %s, %s, %s, %s)
    """, (update.effective_user.id, "video", video_url[:200], sent, failed))
    conn.commit()

    await update.message.reply_text(
        f"✅ Broadcast video completato!\n"
        f"📤 Inviati: {sent}\n"
        f"❌ Falliti: {failed}"
    )

# ================= GESTIONE COMANDI PERSONALIZZATI =================
async def handle_custom_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i comandi personalizzati"""
    message_text = update.message.text
    if not message_text.startswith("/"):
        return

    command = message_text[1:].split()[0].lower()

    cursor.execute("SELECT response_text FROM custom_commands WHERE command_name = %s", (command,))
    result = cursor.fetchone()

    if result:
        await update.message.reply_text(result[0])

# ================= GESTIONE MESSAGGI =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestore principale"""
    user_id = update.effective_user.id
    update_active(user_id)

    # Gestione broadcast
    await handle_broadcast(update, context)

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    # Comandi principali
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("stats", stats))

    # Comandi admin
    app.add_handler(CommandHandler("aggiungi_comando", aggiungi_comando))
    app.add_handler(CommandHandler("elimina_comando", elimina_comando))
    app.add_handler(CommandHandler("broa