import os
import asyncio
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

# ================= CONFIGURAZIONE =================
TOKEN = os.getenv("BOT_TOKEN")  # IMPOSTA NELLE VARIABILI DI RAILWAY
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # IL TUO ID TELEGRAM
DATABASE_URL = os.getenv("DATABASE_URL")  # URL DEL DATABASE POSTGRESQL

# ================= DATABASE =================
def setup_database():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                type VARCHAR(20) NOT NULL  -- 'text', 'photo', 'video'
            )
        """)
        conn.commit()
        return conn
    except Exception as e:
        print(f"❌ ERRORE DATABASE: {e}")
        return None

# ================= COMANDI PRINCIPALI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("👑 Admin", callback_data="admin")]
    ]
    await update.message.reply_text(
        "👋 **Benvenuto!**\n\n"
        "Usa i pulsanti sotto per navigare nel bot.\n"
        "Se sei l'admin, premi su **👑 Admin**.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 **INFO BOT**\n\n"
        "Questo è un bot Telegram personalizzato creato con Python.\n"
        "Funzionalità:\n"
        "✅ Gestione comandi\n"
        "✅ Broadcast messaggi\n"
        "✅ Pannello admin\n"
        "✅ Database PostgreSQL"
    )

async def canali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 **CANALI**\n\n"
        "Ecco i nostri canali Telegram:\n"
        "🔹 [Canale 1](https://t.me/canale1)\n"
        "🔹 [Canale 2](https://t.me/canale2)"
    )

async def contatti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 **CONTATTI**\n\n"
        "🔹 Telegram: [@ContattiBot](https://t.me/ContattiBot)\n"
        "🔹 WhatsApp: [+39 123 456 7890](https://wa.me/391234567890)\n"
        "🔹 Email: info@esempio.com"
    )

# ================= PANNELLO ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 **Accesso negato!** Solo l'admin può usare questo comando.")
        return

    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Aggiungi comando", callback_data="add_command")],
        [InlineKeyboardButton("➖ Elimina comando", callback_data="remove_command")],
        [InlineKeyboardButton("📊 Statistiche", callback_data="stats")]
    ]
    await update.message.reply_text(
        "👑 **PANNELLO ADMIN**\n\n"
        "Scegli un'opzione:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 **Accesso negato!**")
        return

    await update.message.reply_text(
        "📢 **BROADCAST**\n\n"
        "Invia un messaggio a tutti gli utenti.\n\n"
        "Scrivi il messaggio che vuoi inviare (può includere testo, foto o video)."
    )
    # Salva lo stato per gestire il broadcast successivo
    context.user_data['broadcast_mode'] = True

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'broadcast_mode' not in context.user_data:
        return

    if update.message.text:
        # Broadcast testo
        sent = 0
        removed = 0
        try:
            conn = setup_database()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            for user in users:
                try:
                    await context.bot.send_message(chat_id=user[0], text=update.message.text)
                    sent += 1
                except:
                    removed += 1
            conn.close()
            await update.message.reply_text(f"✅ Inviato: {sent}\n🧹 Rimossi: {removed}")
        except Exception as e:
            await update.message.reply_text(f"❌ ERRORE: {e}")
    elif update.message.photo:
        # Broadcast foto
        photo = update.message.photo[-1].file_id
        sent = 0
        removed = 0
        try:
            conn = setup_database()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            for user in users:
                try:
                    await context.bot.send_photo(chat_id=user[0], photo=photo)
                    sent += 1
                except:
                    removed += 1
            conn.close()
            await update.message.reply_text(f"✅ Foto inviata: {sent}\n🧹 Rimossi: {removed}")
        except Exception as e:
            await update.message.reply_text(f"❌ ERRORE: {e}")
    elif update.message.video:
        # Broadcast video
        video = update.message.video.file_id
        sent = 0
        removed = 0
        try:
            conn = setup_database()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            for user in users:
                try:
                    await context.bot.send_video(chat_id=user[0], video=video)
                    sent += 1
                except:
                    removed += 1
            conn.close()
            await update.message.reply_text(f"✅ Video inviato: {sent}\n🧹 Rimossi: {removed}")
        except Exception as e:
            await update.message.reply_text(f"❌ ERRORE: {e}")

    # Resetta lo stato
    del context.user_data['broadcast_mode']

# ================= GESTIONE COMANDI =================
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 **Accesso negato!**")
        return

    await update.message.reply_text(
        "➕ **AGGIUNGI COMANDO**\n\n"
        "Scrivi il comando nel formato:\n"
        "`/nomecomando descrizione tipo`\n\n"
        "Esempi:\n"
        "`/meteo Ottieni previsioni meteo text`\n"
        "`/foto Mostra una foto photo`\n"
        "`/video Mostra un video video`"
    )
    context.user_data['add_command_mode'] = True

async def handle_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'add_command_mode' not in context.user_data:
        return

    try:
        parts = update.message.text.split()
        if len(parts) < 3:
            raise ValueError("Formato non valido")

        name = parts[0].lstrip('/')
        description = ' '.join(parts[1:-1])
        command_type = parts[-1].lower()

        if command_type not in ['text', 'photo', 'video']:
            raise ValueError("Tipo non valido (usa 'text', 'photo' o 'video')")

        conn = setup_database()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO commands (name, description, type) VALUES (%s, %s, %s) "
            "ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description, type = EXCLUDED.type",
            (name, description, command_type)
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Comando **/{name}** aggiunto con successo!")
    except Exception as e:
        await update.message.reply_text(f"❌ ERRORE: {e}")

    del context.user_data['add_command_mode']

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 **Accesso negato!**")
        return

    await update.message.reply_text(
        "➖ **ELIMINA COMANDO**\n\n"
        "Scrivi il nome del comando da eliminare (senza /).\n"
        "Esempio: `meteo`"
    )
    context.user_data['remove_command_mode'] = True

async def handle_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'remove_command_mode' not in context.user_data:
        return

    try:
        command_name = update.message.text.strip()

        conn = setup_database()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM commands WHERE name = %s", (command_name,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            await update.message.reply_text(f"✅ Comando **/{command_name}** eliminato con successo!")
        else:
            await update.message.reply_text(f"⚠️ Comando **/{command_name}** non trovato!")
    except Exception as e:
        await update.message.reply_text(f"❌ ERRORE: {e}")

    del context.user_data['remove_command_mode']

# ================= GESTIONE PULSANTI =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "info":
        await info(update, context)
    elif query.data == "canali":
        await canali(update, context)
    elif query.data == "contatti":
        await contatti(update, context)
    elif query.data == "admin":
        await admin(update, context)
    elif query.data == "broadcast":
        await broadcast(update, context)
    elif query.data == "add_command":
        await add_command(update, context)
    elif query.data == "remove_command":
        await remove_command(update, context)
    elif query.data == "stats":
        await stats(update, context)

# ================= STATISTICHE =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 **Accesso negato!**")
        return

    try:
        conn = setup_database()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM commands")
        commands_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        conn.close()

        await update.message.reply_text(
            "📊 **STATISTICHE**\n\n"
            f"🔹 Comandi registrati: {commands_count}\n"
            f"🔹 Utenti registrati: {users_count}\n"
            "🔹 Database: PostgreSQL"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ ERRORE: {e}")

# ================= GESTIONE UTENTI =================
async def handle_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = setup_database()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (update.effective_user.id, update.effective_user.username, update.effective_user.first_name))
    conn.commit()
    conn.close()

# ================= MAIN =================
async def main():
    # Connetti al database
    conn = setup_database()
    if not conn:
        print("❌ ERRORE: Non riesco a connettermi al database!")
        return

    # Crea l'applicazione Telegram
    application = Application.builder().token(TOKEN).build()

    # Aggiungi gestori (handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("contatti", contatti))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast))
    application.add_handler(MessageHandler(filters.PHOTO, handle_broadcast))
    application.add_handler(MessageHandler(filters.VIDEO, handle_broadcast))
    application.add_handler(MessageHandler(filters.COMMAND, handle_users))

    # Avvia il bot
    print("✅ BOT ONLINE PERFETTO")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
