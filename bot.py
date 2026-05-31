
import os
from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "DEMO")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get("http://localhost:8000/api/v1/status", timeout=5).json()
        msg = f"""🛡️ TrueROAS Status

💰 Spend (7d): ${r['spend']}
📈 True ROAS: {r['true_roas']}x
🤥 Meta ROAS: {r['meta_roas']}x
⚠️ Overstatement: {r['overstatement_pct']}%

Mode: {r['status']}"""
    except:
        msg = "API ажиллахгүй байна. python main.py ажиллуулна уу"
    await update.message.reply_text(msg)

if TOKEN == "DEMO":
    print("Telegram token байхгүй - bot.py алгасна. /api/v1/status ашиглана уу")
else:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("status", status))
    print("Bot ажиллаж байна...")
    app.run_polling()
