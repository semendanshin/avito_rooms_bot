from telegram import Update
from telegram.ext import ContextTypes

from .static_text import START_TEXT


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        START_TEXT,
    )
