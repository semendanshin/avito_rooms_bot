from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database.models import Advertisement, Inspection
from database.types import AdvertisementStatus, DataToGather, AdvertisementResponse

from bot.utils.utils import validate_message_text, delete_message_or_skip
from bot.utils.resend_old_message import check_and_resend_old_message

from bot.service import advertisement as advertisement_service
from bot.service import user as user_service

from .static_text import INSPECTION_PLANING_TEMPLATE
from .manage_data import InspectionPlaningConversationSteps, InspectionTimePeriods
from .keyboards import get_time_periods_keyboard, get_confirm_keyboard, get_inspection_review_keyboard

from bot.handlers.rooms.manage_data import fill_first_room_template

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, time
import re


async def start_inspection_planing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message = await check_and_resend_old_message(update, context)

    await update.callback_query.answer()

    data = update.callback_query.data.split('_')[-1]

    context.user_data['inspection'] = Inspection()
    context.user_data['inspection'].advertisement_id = int(data)

    context.user_data['effective_message'] = effective_message

    message = await update.callback_query.message.reply_text(
        'Введите дату осмотра в формате ДД.ММ'
    )

    context.user_data['messages_to_delete'] = [message]

    return InspectionPlaningConversationSteps.GET_DATE


async def save_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await validate_message_text(update, context, r'\d\d\.\d\d'):
        return InspectionPlaningConversationSteps.GET_DATE

    day, month = map(int, update.message.text.split('.'))

    inspection_date = date(date.today().year, month, day)

    if inspection_date < date.today():
        message = await update.message.reply_text(
            'Дата не может быть раньше сегодняшнего дня. Введите дату осмотра в формате ДД.ММ'
        )
        context.user_data['messages_to_delete'] += [update.message, message]
        return InspectionPlaningConversationSteps.GET_DATE

    context.user_data['inspection'].inspection_date = inspection_date

    message = await update.message.reply_text(
        'Выберите время осмотра',
        reply_markup=get_time_periods_keyboard(),
    )

    context.user_data['messages_to_delete'] += [update.message, message]

    return InspectionPlaningConversationSteps.GET_TIME


async def save_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data = update.callback_query.data.split('_')[-1]

    period = InspectionTimePeriods[data]

    context.user_data['inspection'].inspection_period_start = period.value[0]
    context.user_data['inspection'].inspection_period_end = period.value[1]

    message = await update.callback_query.message.reply_text(
        'Введите контактные данные и имя:\n'
        '<i>Пример: 89999999999 А-Петр</i>',
        parse_mode='HTML',
    )

    context.user_data['messages_to_delete'] += [message]

    return InspectionPlaningConversationSteps.GET_CONTACT_INFO


async def save_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'((\+7|8)?(\d{10}))[\s-]*([АСПЖаспж])[\s-](.*)'

    if not await validate_message_text(update, context, pattern):
        return InspectionPlaningConversationSteps.GET_CONTACT_INFO

    match = re.fullmatch(pattern, update.message.text)

    phone_number = match.group(1)
    status = match.group(4).upper()
    contact_name = match.group(5).capitalize()

    if phone_number.startswith('+7'):
        phone_number = phone_number[2:]

    if phone_number.startswith('9'):
        phone_number = '8' + phone_number

    context.user_data['inspection'].contact_phone = phone_number
    context.user_data['inspection'].contact_name = contact_name
    context.user_data['inspection'].contact_status = status

    message = await update.message.reply_text(
        'Как найти место встречи? (одно фото и/или текст)'
    )

    context.user_data['messages_to_delete'] += [update.message, message]

    return InspectionPlaningConversationSteps.GET_METING_TIP


async def save_meting_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None

    if photo:
        text = update.message.caption if update.message.caption else ''
    else:
        text = update.message.text if update.message.text else ''

    context.user_data['inspection'].meting_tip_text = text
    context.user_data['inspection'].meting_tip_photo_id = photo.file_id if photo else None

    for el in context.user_data['messages_to_delete']:
        await el.delete()
    await update.message.delete()

    meting_tip_text = context.user_data["inspection"].meting_tip_text

    try:
        session: AsyncSession = context.session
    except AttributeError:
        raise AttributeError('Session not found in context')

    advertisement = await advertisement_service.get_advertisement(
        session,
        context.user_data["inspection"].advertisement_id
    )
    await session.refresh(advertisement, attribute_names=["room"])

    text = INSPECTION_PLANING_TEMPLATE.format(
        address=advertisement.room.address + ' кв. ' + advertisement.room.flat_number,
        # day_of_week=context.user_data["inspection"].inspection_date.strftime("%a"),
        day_of_week='',
        inspection_date=context.user_data["inspection"].inspection_date.strftime("%d.%m"),
        inspection_period_start=context.user_data["inspection"].inspection_period_start.strftime("%H:%M"),
        inspection_period_end=context.user_data["inspection"].inspection_period_end.strftime("%H:%M"),
        contact_phone=context.user_data["inspection"].contact_phone,
        contact_status=context.user_data["inspection"].contact_status,
        contact_name=context.user_data["inspection"].contact_name,
        meting_tip_text=f"({meting_tip_text})" if meting_tip_text else '',
    )

    if context.user_data["inspection"].meting_tip_photo_id:
        message = await update.message.reply_photo(
            photo=context.user_data["inspection"].meting_tip_photo_id,
            caption=text,
            reply_markup=get_confirm_keyboard(),
        )
    else:
        message = await update.message.reply_text(
            text,
            reply_markup=get_confirm_keyboard(),
        )

    context.user_data['messages_to_delete'] = [message]

    return InspectionPlaningConversationSteps.CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inspection = context.user_data['inspection']

    try:
        session: AsyncSession = context.session
    except AttributeError:
        raise AttributeError('Session not found in context')

    session.add(inspection)

    advertisement = await advertisement_service.get_advertisement(session, inspection.advertisement_id)
    await session.refresh(advertisement, attribute_names=["room"])
    await session.refresh(advertisement.room, attribute_names=["rooms_info"])
    await session.refresh(advertisement, attribute_names=["added_by"])
    advertisement = AdvertisementResponse.model_validate(advertisement)

    data = DataToGather(
        **advertisement.model_dump(),
        **advertisement.room.model_dump(),
    )

    advertisement.status = AdvertisementStatus.ASSIGNED

    await session.commit()

    await update.callback_query.answer(
        'Осмотр запланирован',
        show_alert=True,
    )

    text = fill_first_room_template(data)
    text += '\n' + INSPECTION_PLANING_TEMPLATE.format(
        address=advertisement.room.address + ' кв. ' + advertisement.room.flat_number,
        # day_of_week=inspection.inspection_date.strftime("%a"),
        day_of_week='',
        inspection_date=inspection.inspection_date.strftime("%d.%m"),
        inspection_period_start=inspection.inspection_period_start.strftime("%H:%M"),
        inspection_period_end=inspection.inspection_period_end.strftime("%H:%M"),
        contact_phone=inspection.contact_phone,
        contact_status=inspection.contact_status,
        contact_name=inspection.contact_name,
        meting_tip_text=inspection.meting_tip_text,
    )

    for user in await user_service.get_admins(session):
        message = await context.bot.send_photo(
            photo=data.plan_telegram_file_id,
            reply_markup=get_inspection_review_keyboard(advertisement_id=advertisement.advertisement_id),
            chat_id=user.id,
            caption=text,
            parse_mode='HTML',
        )
        context.bot_data[user.id] = message.id

    await update.effective_message.edit_reply_markup(reply_markup=None)
    effective_message = context.user_data['effective_message']
    await effective_message.edit_reply_markup(reply_markup=None)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer(
        'Создание осмотра отменено',
        show_alert=True,
    )

    for el in context.user_data.get('messages_to_delete', []):
        await delete_message_or_skip(el)

    await delete_message_or_skip(update.effective_message)

    return ConversationHandler.END


async def cancel_inspection_planing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for el in context.user_data['messages_to_delete']:
        await delete_message_or_skip(el)

    await delete_message_or_skip(update.effective_message)

    await update.message.reply_text(
        'Создание осмотра отменено'
    )

    return ConversationHandler.END
