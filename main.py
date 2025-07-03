import os
import asyncio
import logging
from datetime import datetime, timedelta

import pytz
from telegram import Update, Poll, Message
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackContext
)
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)

# Bot config
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])       # e.g. -1002160364008
THREAD_ID = int(os.environ["THREAD_ID"])   # e.g. 5914

# --- Utils ---
def get_next_tuesday_date() -> str:
    london = pytz.timezone("Europe/London")
    today = datetime.now(london)
    days_ahead = (1 - today.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_tuesday = today + timedelta(days=days_ahead)
    return next_tuesday.strftime("%-d %B")

# --- Admin check ---
async def is_user_admin(update: Update, context: CallbackContext) -> bool:
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in ("administrator", "creator")

# --- Poll sender ---
async def send_weekly_poll(application) -> None:
    question_date = get_next_tuesday_date()
    question = f"{question_date} London Valley"
    options = ["2030 - 2130", "2130 - 2230"]

    try:
        # 先發 poll
        message: Message = await application.bot.send_poll(
            chat_id=CHAT_ID,
            question=question,
            options=options,
            is_anonymous=False,
            allows_multiple_answers=True,
            message_thread_id=THREAD_ID
        )

        # Pin poll
        await application.bot.pin_chat_message(
            chat_id=CHAT_ID,
            message_id=message.message_id,
            disable_notification=True
        )
        logging.info(f"📌 Poll sent and pinned for {question_date}")

    except Exception as e:
        logging.error(f"❌ Failed to send/pin poll: {e}")

# --- Manual command (/pollBadminton) ---
async def manual_poll_badminton(update: Update, context: CallbackContext) -> None:
    if not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only admins can trigger the poll.")
        return

    await send_weekly_poll(context.application)

# --- Main function ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("pollBadminton", manual_poll_badminton))

    london_tz = pytz.timezone("Europe/London")
    scheduler = BackgroundScheduler(timezone=london_tz)
    scheduler.add_job(
        lambda: asyncio.run(send_weekly_poll(app)),
        trigger='cron',
        day_of_week='wed',
        hour=0,
        minute=0
    )
    scheduler.start()

    print("✅ Bot running. Poll every Wednesday 00:00 UK time")
    app.run_polling()

if __name__ == '__main__':
    main()