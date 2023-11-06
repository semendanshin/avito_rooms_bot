from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database.models import User
from database.enums import UserRole

from bot.service import user as user_service

from .keyboards import get_roles_keyboard, get_confirmation_keyboard
from .manage_data import AddRoleConversationSteps

from bot.utils.utils import validate_message_text, delete_message_or_skip, delete_messages

from bot.handlers.rooms.manage_data import fill_user_fio_template

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

        await delete_message_or_skip(update.message)
        await delete_message_or_skip(message)

        return ConversationHandler.END

    message = await update.message.reply_text(
        'Введите юзернейм пользователя из телеграмма (начинается с @), которому хотите дать роль:',
    )

    await delete_message_or_skip(update.message)
    context.user_data['messages_to_delete'] = [message]
    context.user_data['effective_message'] = update.effective_message
    context.user_data[update.effective_message.id] = dict()
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
        context.user_data['messages_to_delete'] += [message, update.effective_message]
        return

    effective_message_id = context.user_data['effective_message'].id
    context.user_data[effective_message_id]['username'] = username

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    message = await update.message.reply_text(
        'Выберите роль:',
        reply_markup=get_roles_keyboard(),
    )
    context.user_data['messages_to_delete'] += [update.message, message]
    return AddRoleConversationSteps.GET_ROLE


async def save_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    role = update.callback_query.data.split('_')[-1]

    role = UserRole(role)

    effective_message_id = context.user_data['effective_message'].id
    context.user_data[effective_message_id]['role'] = role

    username = context.user_data.get(effective_message_id, {}).get('username')

    await delete_messages(context)

    message = await update.effective_message.reply_text(
        f'Вы уверены, что хотите дать пользователю @{username} роль {role.value}?',
        reply_markup=get_confirmation_keyboard(),
    )
    context.user_data['messages_to_delete'] += [message]
    return AddRoleConversationSteps.CONFIRM_ROLE


async def confirm_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    answer = update.callback_query.data.split('_')[-1]

    if answer.isdigit() and int(answer):

        try:
            session = context.session
        except AttributeError:
            raise Exception('Session is not in context')

        effective_message_id = context.user_data['effective_message'].id
        username = context.user_data[effective_message_id]['username']

        user = await user_service.get_user_by_username(session, username)

        await delete_messages(context)

        if any([user.system_first_name, user.system_last_name, user.system_sur_name, user.phone_number]):
            await update_user(update, context)

            return ConversationHandler.END
        else:
            message = await update.effective_message.reply_text(
                'Введите ФИО:',
            )
            context.user_data['messages_to_delete'] += [update.message, message]
        return AddRoleConversationSteps.GET_FIO
    else:
        await delete_messages(context)
        message = await update.effective_message.reply_text(
            'Выберите роль:',
            reply_markup=get_roles_keyboard(),
        )
        context.user_data['messages_to_delete'] += [message]
        return AddRoleConversationSteps.GET_ROLE


async def save_fio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$'

    if not await validate_message_text(update, context, pattern):
        return AddRoleConversationSteps.GET_FIO

    fio = update.message.text

    last_name, first_name, sur_name = fio.split(' ')

    effective_message_id = context.user_data['effective_message'].id
    context.user_data[effective_message_id]['first_name'] = first_name
    context.user_data[effective_message_id]['last_name'] = last_name
    context.user_data[effective_message_id]['sur_name'] = sur_name

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    message = await update.message.reply_text(
        'Введите номер телефона:',
    )
    context.user_data['messages_to_delete'] += [update.message, message]
    return AddRoleConversationSteps.GET_PHONE


async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'((\+7|8)?(\d{10}))'
    if not await validate_message_text(update, context, pattern):
        return AddRoleConversationSteps.GET_PHONE

    phone_number = update.message.text

    if phone_number.startswith('+7'):
        phone_number = phone_number[2:]

    if phone_number.startswith('9'):
        phone_number = '8' + phone_number

    effective_message_id = context.user_data['effective_message'].id
    data = context.user_data[effective_message_id]
    data['phone'] = phone_number

    await update_user(update, context)

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    return ConversationHandler.END


async def update_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message'].id
    data = context.user_data[effective_message_id]

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    user: User = await user_service.get_user_by_username(session, data['username'])

    if not user:
        raise Exception('User not found')

    user.system_first_name = data.get('first_name') if data.get('first_name') else user.system_first_name
    user.system_last_name = data.get('last_name') if data.get('last_name') else user.system_last_name
    user.system_sur_name = data.get('sur_name') if data.get('sur_name') else user.system_sur_name
    user.phone_number = data.get('phone') if data.get('phone') else user.phone_number
    user.role = data.get('role') if data.get('role') else user.role

    await session.commit()

    template = 'Добавлен/обновлен пользователь:\n{role}\n{first_name} {last_name_letter}{sur_name_letter}\n{username}\n{phone_number}'

    text = template.format(
        role=user.role.value,
        first_name=user.system_first_name if user.system_first_name else '',
        last_name_letter=user.system_last_name[0] + '.' if user.system_last_name else '',
        sur_name_letter=user.system_sur_name[0] + '.' if user.system_sur_name else '',
        username='@' + user.username if user.username else '',
        phone_number=user.phone_number if user.phone_number else '',
    )

    await update.effective_message.reply_text(
        text,
    )
    await context.bot.send_message(
        chat_id=user.id,
        text=f'Для вас установлена роль {user.role.value}',
    )


async def cancel_role_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)
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
    agents = await user_service.get_agents(session)

    await update.message.reply_text(
        'Управляющие:\n' + '\n'.join([f'{fill_user_fio_template(el)} - @{el.username}' for el in admins]) + '\n\n' +
        'Диспетчеры:\n' + '\n'.join([f'{fill_user_fio_template(el)} - @{el.username}' for el in dispatchers]) + '\n\n' +
        'Агенты:\n' + '\n'.join([f'{fill_user_fio_template(el)} - @{el.username}' for el in agents]),
    )
