import logging
from telegram import Update, Message
from telegram.ext import ContextTypes

from database.types import DataToGather

from bot.utils.utils import delete_message_or_skip

from bot.service import advertisement as advertisement_service
from bot.service import inspection as inspection_service

from bot.handlers.rooms.keyboards import get_review_keyboard
from bot.handlers.rooms.manage_data import get_data_by_advertisement, fill_first_room_template

from bot.handlers.review.keyboards import get_plan_inspection_keyboard

from bot.handlers.inspection_planing.keyboards import get_inspection_review_keyboard
from bot.handlers.inspection_planing.static_text import INSPECTION_PLANING_TEMPLATE

from database.enums import AdvertisementStatus


async def resend_old_message(update: Update, context: ContextTypes) -> Message:
    from bot.handlers.rooms.handlers import get_appropriate_text, get_appropriate_keyboard, edit_caption_or_text

    advertisement_id = int(update.callback_query.data.split('_')[-1])
    print(advertisement_id)
    if advertisement_id == -1:
        effective_message_id = update.effective_message.message_id
        data: DataToGather = context.user_data[effective_message_id]

        text = get_appropriate_text(data)
        keyboard = get_appropriate_keyboard(-1, data)

        if data.plan_telegram_file_id:
            message = await update.effective_message.reply_photo(
                photo=data.plan_telegram_file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode='HTML',
            )
        else:
            message = await update.effective_message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True,
            )

        context.user_data[message.id] = data
    else:
        advertisement = await advertisement_service.get_advertisement(context.session, advertisement_id)
        await context.session.refresh(advertisement, ['room'])
        await context.session.refresh(advertisement.room, ['rooms_info'])
        await context.session.refresh(advertisement, ['added_by'])

        if advertisement:
            print(advertisement.status)

            data = await get_data_by_advertisement(advertisement)
            text = get_appropriate_text(data)

            if advertisement.status == AdvertisementStatus.NEW:
                message = await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=advertisement.room.plan_telegram_file_id,
                    caption=text,
                    reply_markup=get_review_keyboard(advertisement_id=advertisement.id),
                    parse_mode='HTML',
                )
            if advertisement.status == AdvertisementStatus.VIEWED:

                message = await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=advertisement.room.plan_telegram_file_id,
                    caption=text,
                    reply_markup=get_plan_inspection_keyboard(advertisement_id=advertisement.id),
                    parse_mode='HTML',
                )
            if advertisement.status == AdvertisementStatus.ASSIGNED:
                text = fill_first_room_template(data)

                inspection = await inspection_service.get_inspection_by_advertisement_id(
                    context.session,
                    advertisement_id=advertisement.advertisement_id,
                )

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

                message = await context.bot.send_photo(
                    photo=data.plan_telegram_file_id,
                    reply_markup=get_inspection_review_keyboard(advertisement_id=advertisement.advertisement_id),
                    chat_id=update.effective_chat.id,
                    caption=text,
                    parse_mode='HTML',
                )

    if not await delete_message_or_skip(update.effective_message):
        await edit_caption_or_text(
            update.effective_message,
            'Объявление было перенесено вниз.',
        )

    # await update.callback_query.answer(
    #     'Объявление было перенесено вниз.',
    #     show_alert=True,
    # )

    context.bot_data[update.effective_user.id] = message.id

    return message


async def check_and_resend_old_message(update: Update, context: ContextTypes) -> Message:
    if update.effective_message.id != context.bot_data.get(update.effective_user.id, -1):
        message = await resend_old_message(update, context)
        effective_message = message
    else:
        effective_message = update.effective_message
    context.user_data["effective_message_id"] = effective_message.id
    context.user_data["effective_message"] = effective_message
    return effective_message
