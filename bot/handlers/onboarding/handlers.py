from telegram import Update
from telegram.ext import ContextTypes

from database.enums import UserRole

from .static_text import START_TEXT_1, START_TEXT_2
from .keyboards import get_dispatcher_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = context.database_user
    except AttributeError:
        raise Exception('User is not in context')

    if user.role == UserRole.USER:
        await update.message.reply_text(
            START_TEXT_1,
        )
        await update.message.reply_text(
            START_TEXT_2,
        )
    elif user.role == UserRole.ADMIN:
        await update.message.reply_text(
            'Вы админ',
        )
    elif user.role == UserRole.DISPATCHER:
        await update.message.reply_text(
            'Вы диспетчер',
            reply_markup=get_dispatcher_keyboard(),
        )
