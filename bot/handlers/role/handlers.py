from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from .manage_data import AddRoleConversationSteps
from database.models import User
from database.enums import UserRole
from bot.service import user as user_service
from .keyboards import get_roles_keyboard


async def start_give_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user: User = context.database_user
    except AttributeError:
        raise Exception('User is not in context')

    if user.role != UserRole.ADMIN:
        await update.message.reply_text(
            'У вас нет прав для этого действия',
        )
        return ConversationHandler.END

    await update.message.reply_text(
        'Юзернейм пользователя, которому хотите дать роль:',
    )
    return AddRoleConversationSteps.GET_USERNAME


async def save_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    if not await user_service.get_user_by_username(session, username):
        await update.message.reply_text(
            'Пользователь не найден',
        )
        return ConversationHandler.END

    context.user_data['user_to_give_role'] = username

    await update.message.reply_text(
        'Выберите роль:',
        reply_markup=get_roles_keyboard(),
    )
    return AddRoleConversationSteps.GET_ROLE


async def save_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    role = update.callback_query.data.split('_')[-1]

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    try:
        user: User = context.database_user
    except AttributeError:
        raise Exception('User is not in context')

    if user.role != UserRole.ADMIN:
        await update.message.reply_text(
            'У вас нет прав для этого действия',
        )
        return ConversationHandler.END

    username = context.user_data.get('user_to_give_role')
    if not username:
        await update.message.reply_text(
            'Пользователь не найден',
        )
        return ConversationHandler.END

    role = UserRole(role)

    await user_service.update_user_role(session, username, role)

    await update.effective_message.reply_text(
        'Роль успешно изменена',
    )


async def cancel_role_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Отмена',
    )
    return ConversationHandler.END
