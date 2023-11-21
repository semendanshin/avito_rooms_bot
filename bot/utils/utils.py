from telegram import Update, Message
from telegram.ext import ContextTypes

from logging import getLogger

import re


logger = getLogger(__name__)


def cadnum_to_id(cadnum: str) -> int:
    return int(cadnum.replace(':', '')[-8:])


async def validate_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE, pattern: str) -> bool:
    if not re.fullmatch(pattern, update.message.text):
        message = await update.message.reply_text(
            'Неправильный формат ввода',
        )
        context.user_data["messages_to_delete"].extend([message, update.message])
        return False
    return True


async def delete_message_or_skip(message: Message) -> bool:
    try:
        await message.delete()
        return True
    except Exception as e:
        logger.error(e)
        return False


async def delete_messages(context: ContextTypes.DEFAULT_TYPE):
    for message in context.user_data.get("messages_to_delete", []):
        await delete_message_or_skip(message)
    context.user_data["messages_to_delete"] = []
