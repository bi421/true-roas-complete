from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import httpx
from src.trueroas.core.config import settings


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Use httpx (async) and correct port 8001.
        async with httpx.AsyncClient() as client:
            r = (await client.get(settings.TRUEROAS_API_URL, timeout=5)).json()

        msg = f"""TrueROAS Status

Spend (7d): ${r["spend"]}
True ROAS: {r["true_roas"]}x
Meta ROAS: {r["meta_roas"]}x
Overstatement: {r["overstatement_pct"]}%

Status: {r.get("status", "UNKNOWN")}"""
    except Exception as e:
        msg = f"ALERT: API Unreachable or Error.\nDetail: {str(e)}"
    await update.message.reply_text(msg)


if settings.TELEGRAM_BOT_TOKEN == "DEMO":
    print("Telegram token missing - skipping bot.py. Use /api/v1/status")
else:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", status))
    print("Bot is running...")
    app.run_polling()
