import os
import asyncio
import psycopg2
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from telegram.error import Forbidden, BadRequest

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1092687569
DATABASE_URL = os.getenv("DATABASE_URL")

CHANNELS = [
    "@CAMPANIAVIP"
]

# ================= DATABASE =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

def setup_db():
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

setup_db()

# ================= UTENTE =================
def add_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=%s",(user_id,))
    if cursor.fetchone():
        return False
    cursor.execute("INSERT INTO users (user_id) VALUES (%s)",(user_id,))
    conn.commit()
    return True

# ================= CHECK ISCRIZIONE =================
async def check_sub(user_id, bot):
    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(ch, user_id)
            if m.status not in ["member","administrator","creator"]:
                return False
        except:
            return False
    return True

def sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Entra", url="https://t.me/CAMPANIAVIP")],
        [InlineKeyboardButton("✅ Verifica", callback_data="check")]
    ])

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Promo", callback_data="promo")],
        [InlineKeyboardButton("📢 Canali", callback_data="canali")],
        [InlineKeyboardButton("📞 Contatti", callback_data="contatti")],
        [InlineKeyboardButton("📱 App", callback_data="app")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

   
