from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from .manage_data import AddRoleConversationSteps
from database.models import User
from database.enums import UserRole
from bot.service import user as user_service
from .keyboards import get_roles_keyboard
import asyncio


async def start_give_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user: User = context.database_user
    except AttributeError:
        raise Exception('User is not in context')

    if user.role != UserRole.ADMIN:
        message = await update.message.reply_text(
            'У вас нет прав для этого действия',
        )

        await asyncio.sleep(3)

        await update.message.delete()
        await message.delete()

        return ConversationHandler.END

    message = await update.message.reply_text(
        'Юзернейм пользователя, которому хотите дать роль:',
    )
    context.user_data['messages_to_delete'] = [update.message, message]
    return AddRoleConversationSteps.GET_USERNAME


async def save_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    if username.startswith('@'):
        username = username[1:]

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    if not await user_service.get_user_by_username(session, username):
        message = await update.message.reply_text(
            'Пользователь не найден. Убедитесь, что username введет правильно, и пользователь уже пользовался ботом. '
            'Чтобы отменить, напишите /cancel',
        )
        context.user_data['messages_to_delete'] += [message]
        return

    context.user_data['user_to_give_role'] = username

    message = await update.message.reply_text(
        'Выберите роль:',
        reply_markup=get_roles_keyboard(),
    )
    context.user_data['messages_to_delete'] += [update.message, message]
    return AddRoleConversationSteps.GET_ROLE


async def save_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = update.callback_query.data.split('_')[-1]

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    try:
        user: User = context.database_user
    except AttributeError:
        raise Exception('User is not in context')

    username = context.user_data.get('user_to_give_role')
    if not username:
        await update.message.reply_text(
            'Пользователь не найден',
        )
        return ConversationHandler.END

    role = UserRole(role)

    await user_service.update_user_role(session, username, role)

    await update.callback_query.answer(
        f'Роль пользователя @{username} успешно изменена на {role.value}',
        show_alert=True,
    )
    for el in context.user_data['messages_to_delete']:
        await el.delete()

    return ConversationHandler.END


async def cancel_role_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Отмена',
    )
    return ConversationHandler.END


async def get_users_with_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        return

    dispatchers = await user_service.get_dispatchers(session)
    admins = await user_service.get_admins(session)

    await update.message.reply_text(
        'Управляющие:\n' + '\n'.join([f'@{el.username}' for el in admins]) + '\n\n' +
        'Диспетчеры:\n' + '\n'.join([f'@{el.username}' for el in dispatchers]),
    )
