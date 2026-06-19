import os
from telegram.ext import Application
from database import setup_database
from handlers import setup_handlers

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1092687569"))

def main():
    setup_database()
    app = Application.builder().token(TOKEN).build()
    setup_handlers(app)
    print("✅ BOT ONLINE PERFETTO")
    app.run_polling()

if __name__ == "__main__":
    main()
