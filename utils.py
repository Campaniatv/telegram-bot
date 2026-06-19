from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from database import get_db_connection, log_broadcast

ADMIN_ID = 1092687569

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in context.user_data.get("broadcast", {}):
        context.user_data["broadcast"] = {user_id: True}

    message_type = None
    message_content = None

    if update.message.text:
        message_type = "text"
        message_content = update.message.text
    elif update.message.photo:
        message_type = "photo"
        message_content = "Foto inviata"
    elif update.message.video:
        message_type = "video"
        message_content = "Video inviato"

    if message_type:
        conn, cursor = get_db_connection()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = 0
        failed = 0

        for (uid,) in users:
            try:
                if message_type == "text":
                    await context.bot.send_message(chat_id=uid, text=message_content)
                elif message_type == "photo":
                    await context.bot.send_photo(chat_id=uid, photo=update.message.photo[-1].file_id)
                elif message_type == "video":
                    await context.bot.send_video(chat_id=uid, video=update.message.video.file_id)

                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                failed += 1
                cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
                conn.commit()

        log_broadcast(user_id, message_type, message_content, sent, failed)
        await update.message.reply_text(f"✅ Inviato: {sent}\n🧹 Rimossi: {failed}")
        context.user_data["broadcast"].pop(user_id, None)
