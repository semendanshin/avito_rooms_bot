from telegram import Update
from telegram.ext import ContextTypes

from .static_text import START_TEXT_1, START_TEXT_2


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        START_TEXT_1,
    )
    await update.message.reply_text(
        START_TEXT_2,
    )
