import pprint

import telegram.error
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.crud import advertisement as advertisement_service

from database.enums import RoomTypeEnum, RoomOccupantsEnum, RoomOwnersEnum, RoomStatusEnum, RoomRefusalStatusEnum
from bot.utils.resend_old_message import check_and_resend_old_message
from bot.utils.utils import validate_message_text, delete_message_or_skip, delete_messages
from bot.schemas.types import AdvertisementBase
from bot.handlers.rooms.handlers import edit_caption_or_text, get_appropriate_text, get_appropriate_keyboard
from bot.handlers.inspection_planing.keyboards import get_inspection_review_keyboard

from .manage_data import (
    fill_rooms_info_base_template,
    get_room_info_base_from_advertisement_id, check_rooms_info_base_filled,
    convert_rooms_base_to_rooms_info_base, convert_rooms_info_base_to_rooms_base,
    update_rooms_in_advertisement,
)
from .keyboards import (
    get_rooms_info_base_keyboard,
    get_room_type_keyboard,
    get_room_occupants_keyboard,
    get_room_owners_keyboard,
    get_room_status_keyboard,
    get_room_refusal_status_keyboard,
    get_show_rooms_to_edit_keyboard,
    get_edit_od_delete_keyboard,
    ROOM_TYPE_CALLBACK_DATA,
    ROOM_OCCUPANTS_CALLBACK_DATA,
    ROOM_OWNERS_CALLBACK_DATA,
    ROOM_STATUS_CALLBACK_DATA,
    ROOM_REFUSAL_STATUS_CALLBACK_DATA,
    EDIT_ROOM_CALLBACK_DATA,
    EDIT_OR_DELETE_ROOM_CALLBACK_DATA,
    PICK_ROOM_TO_EDIT_CALLBACK_DATA,
)
from .static_text import TEXTS
from .schemas import RoomsInfoConversationData, RoomInfoBase
from .enums import RoomInfoBaseConversationSteps


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    effective_ad_message = await check_and_resend_old_message(update, context)

    advertisement_id = int(update.callback_query.data.split('_')[-1])

    if advertisement_id == -1:
        advertisement_data: AdvertisementBase = context.user_data[update.callback_query.message.id]
        rooms_info_base = convert_rooms_base_to_rooms_info_base(advertisement_data.flat.rooms)
    else:
        rooms_info_base = await get_room_info_base_from_advertisement_id(context.session, advertisement_id)

    text = fill_rooms_info_base_template(rooms_info_base)
    keyboard = get_rooms_info_base_keyboard()

    message = await update.effective_message.reply_text(text=text, reply_markup=keyboard)

    data = RoomsInfoConversationData(
        advertisement_id=advertisement_id,
        rooms_info_base=rooms_info_base,
        rooms_info_base_message=message,
        effective_ad_message=effective_ad_message,
    )
    context.user_data['rooms_info_data'] = data

    return RoomInfoBaseConversationSteps.SHOW_ROOMS_TO_EDIT


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data: RoomsInfoConversationData = context.user_data['rooms_info_data']

    if not check_rooms_info_base_filled(data.rooms_info_base):
        await update.callback_query.answer(
            text='Заполните все поля',
            show_alert=True,
        )
        return RoomInfoBaseConversationSteps.SHOW_ROOMS_TO_EDIT

    if data.advertisement_id == -1:
        rooms_create = convert_rooms_info_base_to_rooms_base(data.rooms_info_base.rooms)
        advertisement_data: AdvertisementBase = context.user_data[data.effective_ad_message.id]
        advertisement_data.flat.rooms = rooms_create

        keyboard = get_appropriate_keyboard(-1, advertisement_data)
    else:
        rooms_update = convert_rooms_info_base_to_rooms_base(data.rooms_info_base.rooms)
        await update_rooms_in_advertisement(context.session, data.advertisement_id, rooms_update)

        advertisement_data = await advertisement_service.get_advertisement(context.session, data.advertisement_id)
        advertisement_data = await advertisement_service.refresh_advertisement(context.session, advertisement_data)

        keyboard = get_inspection_review_keyboard(advertisement_data.id)

    text = get_appropriate_text(advertisement_data)

    await edit_caption_or_text(
        data.effective_ad_message,
        new_text=text,
        reply_markup=keyboard,
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    await update.callback_query.answer(
        text='Сохранено',
        show_alert=True,
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)
    data = context.user_data.get('rooms_info_data')
    if data:
        await delete_message_or_skip(data.rooms_info_base_message)
        del context.user_data['rooms_info_data']
    return ConversationHandler.END


async def stat_add_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    data.room_info_base = RoomInfoBase()

    message = await update.effective_message.reply_text(text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_NUMBER])
    context.user_data['messages_to_delete'] = [message]

    return RoomInfoBaseConversationSteps.ADD_ROOM_NUMBER


async def add_room_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'^\d+$'

    if not validate_message_text(update, context, pattern):
        return RoomInfoBaseConversationSteps.ADD_ROOM_NUMBER

    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    data.room_info_base.room_number = int(update.effective_message.text)

    message = await update.effective_message.reply_text(text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_AREA])

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    context.user_data['messages_to_delete'] = [message]

    return RoomInfoBaseConversationSteps.ADD_ROOM_AREA


async def add_room_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'^\d+([.,]\d+)?$'

    if update.message.text != '/0':
        if not validate_message_text(update, context, pattern):
            return RoomInfoBaseConversationSteps.ADD_ROOM_AREA

        data: RoomsInfoConversationData = context.user_data['rooms_info_data']
        data.room_info_base.room_area = float(update.effective_message.text.replace(',', '.'))

    message = await update.effective_message.reply_text(
        text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_TYPE],
        reply_markup=get_room_type_keyboard(),
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    context.user_data['messages_to_delete'] = [message]

    return RoomInfoBaseConversationSteps.ADD_ROOM_TYPE


async def add_room_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    callback_data = update.callback_query.data.replace(ROOM_TYPE_CALLBACK_DATA + '_', '')

    if callback_data != 'skip':
        data.room_info_base.room_type = RoomTypeEnum[callback_data]

    await update.effective_message.reply_text(
        text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_STATUS],
        reply_markup=get_room_status_keyboard(),
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    return RoomInfoBaseConversationSteps.ADD_ROOM_STATUS


async def add_room_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    callback_data = update.callback_query.data.replace(ROOM_STATUS_CALLBACK_DATA + '_', '')

    if callback_data != 'skip':
        data.room_info_base.room_status = RoomStatusEnum[callback_data]

    await update.effective_message.reply_text(
        text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS],
        reply_markup=get_room_owners_keyboard(data.room_info_base.room_owners),
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    return RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS


async def add_room_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    callback_data = update.callback_query.data.replace(ROOM_OWNERS_CALLBACK_DATA + '_', '')

    if callback_data in ('done', 'skip'):
        if callback_data == 'skip':
            data.room_info_base.room_owners = {}

        message = await update.effective_message.reply_text(
            text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_REFUSAL_STATUS],
            reply_markup=get_room_refusal_status_keyboard(),
        )

        await delete_messages(context)
        await delete_message_or_skip(update.effective_message)

        context.user_data['messages_to_delete'] = [message]

        return RoomInfoBaseConversationSteps.ADD_ROOM_REFUSAL_STATUS

    owner = RoomOwnersEnum[
        update.callback_query.data.replace(ROOM_OWNERS_CALLBACK_DATA + '_', '')
    ]

    if owner in data.room_info_base.room_owners:
        data.room_info_base.room_owners[owner] += 1
        if data.room_info_base.room_owners[owner] == 4:
            data.room_info_base.room_owners[owner] = 0
    else:
        data.room_info_base.room_owners[owner] = 1

    await update.effective_message.edit_text(
        text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS],
        reply_markup=get_room_owners_keyboard(data.room_info_base.room_owners),
    )

    return RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS


async def add_room_refusal_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    callback_data = update.callback_query.data.replace(ROOM_REFUSAL_STATUS_CALLBACK_DATA + '_', '')

    if callback_data != 'skip':
        data.room_info_base.room_refusal_status = RoomRefusalStatusEnum[callback_data]

    message = await update.effective_message.reply_text(
        text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_COMMENT],
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    context.user_data['messages_to_delete'] = [message]

    return RoomInfoBaseConversationSteps.ADD_ROOM_COMMENT


async def add_room_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data: RoomsInfoConversationData = context.user_data['rooms_info_data']

    if update.message.text != '/0':
        data.room_info_base.comment = update.message.text

    if data.room_info_base.room_status == RoomStatusEnum.NON_LIVING:
        data.room_info_base.room_occupants = {}

        return await save_changes(update, context)

    message = await update.effective_message.reply_text(
        text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS],
        reply_markup=get_room_owners_keyboard(data.room_info_base.room_owners),
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    context.user_data['messages_to_delete'] = [message]

    return RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS


async def add_room_occupants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    callback_data = update.callback_query.data.replace(ROOM_OCCUPANTS_CALLBACK_DATA + '_', '')

    if callback_data in ('done', 'skip'):
        if callback_data == 'skip':
            data.room_info_base.room_occupants = {}

        return await save_changes(update, context)

    occupant = RoomOccupantsEnum[
        update.callback_query.data.replace(ROOM_OCCUPANTS_CALLBACK_DATA + '_', '')
    ]

    if occupant in data.room_info_base.room_occupants:
        data.room_info_base.room_occupants[occupant] += 1
        if data.room_info_base.room_occupants[occupant] == 4:
            data.room_info_base.room_occupants[occupant] = 0
    else:
        data.room_info_base.room_occupants[occupant] = 1

    await update.effective_message.edit_text(
        text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_OCCUPANTS],
        reply_markup=get_room_occupants_keyboard(data.room_info_base.room_occupants),
    )

    return RoomInfoBaseConversationSteps.ADD_ROOM_OCCUPANTS


async def save_changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data: RoomsInfoConversationData = context.user_data['rooms_info_data']

    data.rooms_info_base.rooms.append(data.room_info_base)

    try:
        await data.rooms_info_base_message.edit_text(
            text=fill_rooms_info_base_template(data.rooms_info_base),
            reply_markup=get_rooms_info_base_keyboard(),
        )
    except telegram.error.BadRequest:
        pass

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    data.room_info_base = None

    return RoomInfoBaseConversationSteps.SHOW_ROOMS_TO_EDIT


async def show_rooms_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    await update.effective_message.reply_text(
        text=TEXTS[RoomInfoBaseConversationSteps.PICK_ROOM_TO_DELETE_OR_EDIT],
        reply_markup=get_show_rooms_to_edit_keyboard(data.rooms_info_base.rooms),
    )
    return RoomInfoBaseConversationSteps.PICK_ROOM_TO_DELETE_OR_EDIT


async def pick_room_to_edit_or_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data: RoomsInfoConversationData = context.user_data['rooms_info_data']
    room_number = update.callback_query.data.replace(PICK_ROOM_TO_EDIT_CALLBACK_DATA + '_', '')

    if room_number == 'back':
        await delete_message_or_skip(update.effective_message)
        return RoomInfoBaseConversationSteps.SHOW_ROOMS_TO_EDIT

    room_number = int(room_number)
    data.room_info_base = filter(lambda room: room.room_number == room_number, data.rooms_info_base.rooms).__next__()
    message = await update.effective_message.edit_text(
        text=TEXTS[RoomInfoBaseConversationSteps.CHOOSE_DELETE_OR_EDIT],
        reply_markup=get_edit_od_delete_keyboard(room_number),
    )
    context.user_data['messages_to_delete'] = [message]
    return RoomInfoBaseConversationSteps.CHOOSE_DELETE_OR_EDIT


async def delete_room_or_start_edit(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    callback_data = update.callback_query.data.replace(EDIT_OR_DELETE_ROOM_CALLBACK_DATA + '_', '')
    data = contex.user_data['rooms_info_data']

    if callback_data == 'back':
        await delete_message_or_skip(update.effective_message)
        await data.rooms_info_base_message.edit_text(
            text=fill_rooms_info_base_template(data.rooms_info_base),
            reply_markup=get_rooms_info_base_keyboard(),
        )
        return RoomInfoBaseConversationSteps.SHOW_ROOMS_TO_EDIT

    room_number = int(callback_data.split('_')[-2])
    effective_room = filter(
        lambda room: room.room_number == room_number, data.rooms_info_base.rooms
    ).__next__()

    if callback_data.split('_')[-1] == 'delete':
        data.rooms_info_base.rooms.remove(effective_room)
        await delete_message_or_skip(update.effective_message)
        await data.rooms_info_base_message.edit_text(
            text=fill_rooms_info_base_template(data.rooms_info_base),
            reply_markup=get_rooms_info_base_keyboard(),
        )
        return RoomInfoBaseConversationSteps.SHOW_ROOMS_TO_EDIT
    elif callback_data.split('_')[-1] == 'edit':
        data.rooms_info_base.rooms.remove(effective_room)
        data.room_info_base = effective_room
        await update.effective_message.edit_text(
            text=TEXTS[RoomInfoBaseConversationSteps.ADD_ROOM_AREA],
            reply_markup=None,
        )
        return RoomInfoBaseConversationSteps.ADD_ROOM_AREA
    else:
        await update.effective_message.edit_text(
            text=TEXTS[RoomInfoBaseConversationSteps.CHOOSE_DELETE_OR_EDIT],
            reply_markup=get_edit_od_delete_keyboard(data.room_info_base.room_number),
        )
        return RoomInfoBaseConversationSteps.CHOOSE_DELETE_OR_EDIT
