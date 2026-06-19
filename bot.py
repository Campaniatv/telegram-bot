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
ADMIN_ID = int(os.getenv("ADMIN_ID", "1092687569"))
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DATABASE =================
conn = None
cursor = None

def setup_database():
    global conn, cursor
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
    conn.commit()

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
        [InlineKeyboardButton("🔑 Admin", callback_data="admin")]
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
    await update.message.reply_text(
        "📞 CONTATTI:\n\n"
        "Telegram: @CAMPANIAVIP\n"
        "WhatsApp: https://wa.me/393509741712"
    )

# ================= PULSANTI =================
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
            "Telegram: @CAMPANIAVIP\n"
            "WhatsApp: https://wa.me/393509741712"
        )

    elif query.data == "admin":
        if query.from_user.id != ADMIN_ID:
            await query.edit_message_text("❌ Non sei autorizzato!")
            return
        keyboard = [
            [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("➕ Aggiungi comando", callback_data="add_command")],
            [InlineKeyboardButton("➖ Elimina comando", callback_data="remove_command")]
        ]
        await query.edit_message_text(
            "🔧 PANNELLO ADMIN",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ================= COMANDI ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non sei autorizzato!")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Aggiungi comando", callback_data="add_command")],
        [InlineKeyboardButton("➖ Elimina comando", callback_data="remove_command")]
    ]
    await update.message.reply_text(
        "🔧 PANNELLO ADMIN",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.message.reply_text(
        f"📊 STATISTICHE\n\n"
        f"👥 Totali: {total}\n"
        f"🔥 Oggi: {today}\n"
        f"📅 Mese: {month}"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Non sei autorizzato!")
        return

    user_state[update.effective_user.id] = "broadcast"
    await update.message.reply_text(
        "📢 Invia il messaggio da inviare a tutti gli utenti (testo, foto o video)"
    )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.callback_query.edit_message_text(
        "➕ AGGIUNGI COMANDO\n\n"
        "Scrivi il comando che vuoi aggiungere nel formato:\n"
        "/nuovo_comando [descrizione]\n\n"
        "Esempio: /nuovo_comando Mostra informazioni aggiuntive"
    )
    user_state[update.effective_user.id] = "add_command"

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.callback_query.edit_message_text(
        "➖ ELIMINA COMANDO\n\n"
        "Scrivi il comando che vuoi eliminare (senza /)\n\n"
        "Esempio: nuovo_comando"
    )
    user_state[update.effective_user.id] = "remove_command"

# ================= GESTIONE MESSAGGI =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_active(user_id)

    # Gestione broadcast
    if user_state.get(user_id) == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        blocked = 0  # Contatore per utenti che bloccano il bot

        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                # Non rimuove più l'utente dal database
                blocked += 1
                print(f"⚠️ Utente {uid} ha bloccato il bot o c'è stato un errore: {e}")

        user_state[user_id] = None
        await update.message.reply_text(
            f"✅ Inviato con successo: {sent}\n"
            f"❌ Bloccati/Errori: {blocked}\n"
            f"📊 Totale utenti: {len(users)}"
        )

    # Gestione aggiunta comando
    elif user_state.get(user_id) == "add_command":
        if context.args:
            new_command = context.args[0].lower()
            description = " ".join(context.args[1:]) if len(context.args) > 1 else "Nessuna descrizione"
            await update.message.reply_text(f"✅ Comando /{new_command} aggiunto con descrizione: {description}")
        else:
            await update.message.reply_text("⚠️ Usa: /nuovo_comando [descrizione]")
        user_state[user_id] = None

    # Gestione rimozione comando
    elif user_state.get(user_id) == "remove_command":
        if context.args:
            command_to_remove = context.args[0].lower()
            await update.message.reply_text(f"✅ Comando /{command_to_remove} rimosso")
        else:
            await update.message.reply_text("⚠️ Usa: rimuovi_comando [nome_comando]")
        user_state[user_id] = None

# ================= MAIN (GESTIONE SICURA EVENT LOOP) =================
async def main_async():
    setup_database()
    app = Application.builder().token(TOKEN).build()

    # Comandi principali
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("canali", canali))
    app.add_handler(CommandHandler("contatti", contatti))
    app.add_handler(CommandHandler("admin", admin))

    # Comandi admin
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Pulsanti e messaggi
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

    print("✅ BOT ONLINE PERFETTO")
    await app.run_polling()

def main():
    try:
        if not asyncio.get_event_loop().is_running():
            asyncio.run(main_async())
        else:
            print("⚠️ Event loop già in esecuzione - riavvio in corso...")
            loop = asyncio.get_event_loop()
            loop.create_task(main_async())
    except Exception as e:
        print(f"❌ Errore nel bot: {e}")
        raise

if __name__ == "__main__":
    main()
