from telegram import Update
from telegram.ext import ContextTypes

import re


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