from telegram import Update, Bot
from telegram.ext import ContextTypes, ConversationHandler

from bot.crud import advertisement as advertisement_service
from bot.crud import user as user_service

from bot.utils.utils import delete_messages, delete_message_or_skip
from bot.utils.resend_old_message import check_and_resend_old_message

from bot.handlers.rooms.handlers import get_appropriate_text
from bot.handlers.rooms.manage_data import fill_user_fio_template, refresh_advertisement

from database.enums import AdvertisementStatus, UserRole

from sqlalchemy.ext.asyncio import AsyncSession

from .keyboards import get_plan_inspection_keyboard, get_users_keyboard, get_confirmation_keyboard
from .manage_data import ReviewConversationStates


async def send_advertisement(session, bot: Bot, advertisement_id: int, user_id: int):
    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)

    text = get_appropriate_text(advertisement)

    message = await bot.send_photo(
        chat_id=user_id,
        photo=advertisement.flat.plan_telegram_file_id,
        reply_markup=get_plan_inspection_keyboard(advertisement_id=advertisement_id),
        caption=text,
        parse_mode='HTML',
    )

    return message


async def view_advertisement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message = await check_and_resend_old_message(update, context)

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    advertisement_id = int(update.callback_query.data.split('_')[-1])

    try:
        status = AdvertisementStatus[update.callback_query.data.split('_')[-2]]
    except ValueError:
        await update.effective_message.reply_text(
            "Пропускаю"
        )
    else:
        if status == AdvertisementStatus.VIEWED:
            await update.callback_query.answer()

            context.user_data['review'] = {
                'advertisement_id': advertisement_id,
                'effective_message': effective_message,
            }

            dispatchers = await user_service.get_dispatchers(session)

            if not dispatchers:
                message = await update.effective_message.reply_text(
                    'Диспетчеров нет. Отменяю.'
                )
                context.user_data['messages_to_delete'] += [message]

                await delete_messages(context)
                await delete_message_or_skip(effective_message)

                return ConversationHandler.END

            if len(dispatchers) > 1:
                message = await effective_message.reply_text(
                    'Выберите диспетчера',
                    reply_markup=get_users_keyboard('attach_dispatcher', dispatchers),
                )
                context.user_data['messages_to_delete'] += [message]

                return ReviewConversationStates.CHOOSE_DISPATCHER

            dispatcher = dispatchers[0]

            context.user_data.get('review', {}).update(
                {
                    'dispatcher': dispatcher,
                }
            )

            agents = await user_service.get_agents(session)

            if not agents:
                message = await update.effective_message.reply_text(
                    'Агентов нет. Отменяю.'
                )
                context.user_data['messages_to_delete'] += [message]

                await delete_messages(context)
                await delete_message_or_skip(update.effective_message)

                return ConversationHandler.END

            if len(agents) > 1:
                message = await update.effective_message.reply_text(
                    'Выберите агента',
                    reply_markup=get_users_keyboard('attach_agent', agents),
                )
                context.user_data['messages_to_delete'] += [message]

                return ReviewConversationStates.CHOOSE_AGENT

            agent = agents[0]

            context.user_data.get('review', {}).update(
                {
                    'agent': agents[0],
                }
            )

            dispatcher_fio = fill_user_fio_template(dispatcher)
            agent_fio = fill_user_fio_template(agent)

            message = await update.effective_message.reply_text(
                'Подтвердите выбор:\n'
                f'Диспетчер: {dispatcher_fio}\n'
                f'Агент: {agent_fio}',
                reply_markup=get_confirmation_keyboard(advertisement_id),
            )
            context.user_data['messages_to_delete'] = [message]

            return ReviewConversationStates.CONFIRMATION

        elif status == AdvertisementStatus.CANCELED:
            await update.callback_query.answer(
                'Объявление помечено как отмененное',
                show_alert=True,
            )

            await delete_messages(context)
            await delete_message_or_skip(effective_message)
            await update.effective_message.delete()

            return ConversationHandler.END


async def attach_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data = update.callback_query.data.split('_')

    user_id = int(data[-1])

    try:
        session: AsyncSession = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    dispatcher = await user_service.get_user(session, user_id)

    if not dispatcher:
        message = await update.effective_message.reply_text(
            'Пользователь не является диспетчером'
        )
        context.user_data['messages_to_delete'] += [message]
        return

    if dispatcher.role != UserRole.DISPATCHER:
        message = await update.effective_message.reply_text(
            'Пользователь не является диспетчером'
        )
        context.user_data['messages_to_delete'] += [message]
        return

    context.user_data.get('review', {}).update(
        {
            'dispatcher': dispatcher,
        }
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    agents = await user_service.get_agents(session)

    if not agents:
        message = await update.effective_message.reply_text(
            'Агентов нет. Отменяю.'
        )
        context.user_data['messages_to_delete'] += [message]

        await delete_messages(context)
        await delete_message_or_skip(update.effective_message)

        return ConversationHandler.END

    if len(agents) > 1:
        message = await update.effective_message.reply_text(
            'Выберите агента',
            reply_markup=get_users_keyboard('attach_agent', agents),
        )
        context.user_data['messages_to_delete'] += [message]

        return ReviewConversationStates.CHOOSE_AGENT

    advertisement_id = context.user_data.get('review', {}).get('advertisement_id')

    agent = agents[0]

    context.user_data.get('review', {}).update(
        {
            'agent': agents[0],
        }
    )

    dispatcher_fio = fill_user_fio_template(dispatcher)
    agent_fio = fill_user_fio_template(agent)

    message = await update.effective_message.reply_text(
        'Подтвердите выбор:\n'
        f'Диспетчер: {dispatcher_fio}\n'
        f'Агент: {agent_fio}',
        reply_markup=get_confirmation_keyboard(advertisement_id),
    )
    context.user_data['messages_to_delete'] += [message]

    return ReviewConversationStates.CONFIRMATION


async def attach_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data = update.callback_query.data.split('_')

    user_id = int(data[-1])

    try:
        session: AsyncSession = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    agent = await user_service.get_user(session, user_id)

    if not agent:
        message = await update.effective_message.reply_text(
            'Пользователь не является агентом'
        )
        context.user_data['messages_to_delete'] += [message]
        return

    if agent.role != UserRole.AGENT:
        message = await update.effective_message.reply_text(
            'Пользователь не является агентом'
        )
        context.user_data['messages_to_delete'] += [message]
        return

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    context.user_data.get('review', {}).update(
        {
            'agent': agent,
        }
    )

    dispatcher = context.user_data.get('review', {}).get('dispatcher')
    advertisement_id = context.user_data.get('review', {}).get('advertisement_id')

    if not dispatcher:
        message = await update.effective_message.reply_text(
            'Диспетчер не выбран'
        )
        context.user_data['messages_to_delete'] += [message]
        return

    dispatcher_fio = fill_user_fio_template(dispatcher)
    agent_fio = fill_user_fio_template(agent)

    message = await update.effective_message.reply_text(
        'Подтвердите выбор:\n'
        f'Диспетчер: {dispatcher_fio}\n'
        f'Агент: {agent_fio}',
        reply_markup=get_confirmation_keyboard(advertisement_id),
    )
    context.user_data['messages_to_delete'] += [message]

    return ReviewConversationStates.CONFIRMATION


async def confirm_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split('_')
    answer = data[-1]

    if answer.isdigit() and int(answer):
        try:
            session: AsyncSession = context.session
        except AttributeError:
            raise Exception('Session is not in context')

        advertisement_id = context.user_data.get('review', {}).get('advertisement_id')
        dispatcher = context.user_data.get('review', {}).get('dispatcher')
        agent = context.user_data.get('review', {}).get('agent')
        effective_message = context.user_data.get('review', {}).get('effective_message')

        if not any([advertisement_id, dispatcher, agent]):
            await update.callback_query.answer(
                'Произошла ошибка. Отменяю',
                show_alert=True,
            )
            await delete_messages(context)
            return ConversationHandler.END

        advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
        advertisement = await refresh_advertisement(session, advertisement)

        advertisement.pinned_dispatcher_id = dispatcher.id
        advertisement.pinned_agent_id = agent.id
        advertisement.status = AdvertisementStatus.VIEWED

        await update.callback_query.answer(
            'Отправлено диспетчеру',
            show_alert=True,
        )

        message = await send_advertisement(session, context.bot, advertisement_id, dispatcher.id)

        context.bot_data[dispatcher.id] = message.id

        await session.commit()

        await delete_message_or_skip(effective_message)
    else:
        del context.user_data['review']
        await update.callback_query.answer(
            'Отменено',
            show_alert=True,
        )

    await delete_messages(context)

    return ConversationHandler.END


async def cancel_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Назначение отменено'
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    return ConversationHandler.END
