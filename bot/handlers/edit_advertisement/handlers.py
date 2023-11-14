import pprint

from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes

from bot.handlers.rooms.manage_data import AddRoomDialogStates, refresh_advertisement
from bot.handlers.rooms.handlers import (get_appropriate_text,
                                         update_message_and_delete_messages, edit_caption_or_text)
from bot.handlers.review.keyboards import get_plan_inspection_keyboard
from bot.crud import advertisement as advertisement_service
from bot.crud import room as room_service
from bot.utils.utils import delete_messages, delete_message_or_skip, validate_message_text, cadnum_to_id
from bot.utils.dadata_repository import dadata

from bot.handlers.rooms.keyboards import (
    get_house_is_historical_keyboard,
    get_entrance_type_keyboard,
    get_view_type_keyboard,
    get_toilet_type_keyboard,
    get_yes_or_no_keyboard,
)
from database.models import Advertisement, Room

from database.enums import HouseEntranceType, ViewType, ToiletType, RoomTypeEnum, RoomStatusEnum, RoomOwnersEnum, \
    RoomRefusalStatusEnum, RoomOccupantsEnum

import re

from sqlalchemy.ext.asyncio import AsyncSession


from .manage_data import DataToGather

async def start_edit_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    advertisement_id = int(update.callback_query.data.split('_')[-1])

    message = await update.effective_message.reply_text(
        'Вставьте картинку с планом',
    )

    context.user_data["messages_to_delete"] = [message]
    context.user_data["effective_advertisement_id"] = advertisement_id
    context.user_data["effective_message"] = update.effective_message

    return AddRoomDialogStates.FLAT_PLAN


async def edit_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advertisement_id = context.user_data.get("effective_advertisement_id")
    if not advertisement_id:
        await update.effective_message.reply_text(
            'К сожалению данные для этого сообщения потерялись',
        )
        return ConversationHandler.END

    photo = update.message.photo[-1]

    await delete_messages(context)
    await update.message.delete()

    try:
        session: AsyncSession = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
    await refresh_advertisement(session, advertisement)

    if not advertisement:
        await update.effective_message.reply_text(
            'Объявление не найдено',
        )
        return ConversationHandler.END

    advertisement.flat.telegram_file_id = photo.file_id
    await session.commit()

    keyboard = get_plan_inspection_keyboard(advertisement_id=advertisement_id)

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=get_appropriate_text(advertisement),
        parse_mode='HTML',
        reply_markup=keyboard,
    )
    del context.user_data['effective_advertisement_id']

    effective_message = context.user_data.get("effective_message")
    await delete_message_or_skip(effective_message)

    return ConversationHandler.END


async def cancel_edit_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)
    return ConversationHandler.END


async def start_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    advertisement_id = int(update.callback_query.data.split('_')[-1])

    message = await update.effective_message.reply_text(
        'Вставьте номер телефона',
    )

    context.user_data["messages_to_delete"] = [message]
    context.user_data["effective_advertisement_id"] = advertisement_id
    context.user_data["effective_message"] = update.effective_message

    return AddRoomDialogStates.CONTACT_PHONE


async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_string = update.message.text

    pattern = r'((\+7|8)?(\d{10}))[\s-]*([АВСХавсх])[\s-](.*)'

    match = re.match(pattern, input_string)

    if not match:
        await update.effective_message.reply_text(
            'Неправильный формат ввода',
        )
        context.user_data["messages_to_delete"].append(update.effective_message)
        return

    phone = match.group(1)
    letter = match.group(4).upper()
    name = match.group(5).capitalize()

    print(phone, letter, name)

    if letter in ['В', 'Х']:
        letter = 'С'

    if phone.startswith('+7'):
        phone = '8' + phone[2:]

    if phone.startswith('9'):
        phone = '8' + phone

    advertisement_id = context.user_data.get("effective_advertisement_id")
    if not advertisement_id:
        await update.effective_message.reply_text(
            'К сожалению данные для этого сообщения потерялись',
        )
        return ConversationHandler.END

    advertisement = await advertisement_service.get_advertisement(context.session, advertisement_id)

    if not advertisement:
        await update.effective_message.reply_text(
            'Объявление не найдено',
        )
        return ConversationHandler.END

    await refresh_advertisement(context.session, advertisement)

    advertisement.contact_phone = phone
    advertisement.contact_name = name
    advertisement.contact_status = letter

    await context.session.commit()

    keyboard = get_plan_inspection_keyboard(advertisement_id=advertisement_id)

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=advertisement.flat.plan_telegram_file_id,
        caption=get_appropriate_text(advertisement),
        parse_mode='HTML',
        reply_markup=keyboard,
    )

    del context.user_data['effective_advertisement_id']

    effective_message = context.user_data.get("effective_message")
    await delete_message_or_skip(effective_message)

    await delete_messages(context)
    await update.message.delete()

    return ConversationHandler.END


async def cancel_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления телефона (данные не сохранены)',
    )
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)
    return ConversationHandler.END


async def start_edit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    advertisement_id = int(update.callback_query.data.split('_')[-1])

    message = await update.effective_message.reply_text(
        text='Площадь квартиры (пропустить -> /0)',
    )

    context.user_data["messages_to_delete"] = [message]
    advertisement = await advertisement_service.get_advertisement(context.session, advertisement_id)
    await refresh_advertisement(context.session, advertisement)
    context.user_data["effective_advertisement_id"] = advertisement_id
    context.user_data["effective_message"] = update.effective_message
    context.user_data["data_to_gather"] = DataToGather()

    return AddRoomDialogStates.FLAT_AREA


async def edit_flat_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data: DataToGather = context.user_data.get("data_to_gather")

    if update.message.text != '/0':
        if not validate_message_text(update, context, r'\d+([.,]\d+)?'):
            return

        data.flat_area = float(update.message.text.replace(',', '.'))

    message = await update.effective_message.reply_text(
        text='Высота потолка (пропустить -> /0)',
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.FLAT_HEIGHT


async def edit_flat_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data: DataToGather = context.user_data.get("data_to_gather")

    if update.message.text != '/0':
        if not validate_message_text(update, context, r'\d+([.,]\d+)?'):
            return

        data.flat_height = float(update.message.text.replace(',', '.'))

    await update.effective_message.reply_text(
        text='Дом является памятником?',
        reply_markup=get_house_is_historical_keyboard(-1),
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    return AddRoomDialogStates.HOUSE_IS_HISTORICAL


async def edit_house_is_historical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    data: DataToGather = context.user_data.get("data_to_gather")

    if callback_data.split('_')[-1] != 'skip':
        data.is_historical = bool(int(callback_data.split('_')[-1]))

    await update.effective_message.reply_text(
        text='Есть лифт рядом с квартирой?',
        reply_markup=get_yes_or_no_keyboard(callback_pattern='is_elevator_nearby_'),
    )

    await update.effective_message.delete()

    # await edit_caption_or_text(
    #     context.user_data["effective_message"],
    #     get_appropriate_text(advertisement),
    # )

    return AddRoomDialogStates.ELEVATOR_NEARBY


async def edit_elevator_nearby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    data: DataToGather = context.user_data.get("data_to_gather")

    if callback_data.split('_')[-1] != 'skip':
        data.elevator_nearby = bool(int(callback_data.split('_')[-1]))

    await update.effective_message.delete()

    # await edit_caption_or_text(
    #     context.user_data["effective_message"],
    #     get_appropriate_text(advertisement),
    # )

    advertisement_id = context.user_data.get("effective_advertisement_id")
    advertisement = await advertisement_service.get_advertisement(context.session, advertisement_id)
    await refresh_advertisement(context.session, advertisement)

    if advertisement.flat.flour == 2:
        await update.effective_message.reply_text(
            text='Помещение под этой квартирой жилое?',
            reply_markup=get_yes_or_no_keyboard(callback_pattern='room_under_is_living_'),
        )

        return AddRoomDialogStates.ROOM_UNDER

    data.under_room_is_living = True
    await update.effective_message.reply_text(
        text='Вход в парадную откуда?',
        reply_markup=get_entrance_type_keyboard(advertisement_id=-1),
    )

    return AddRoomDialogStates.ENTRANCE_TYPE


async def edit_room_under(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    data: DataToGather = context.user_data.get("data_to_gather")

    if callback_data.split('_')[-1] != 'skip':
        data.under_room_is_living = bool(int(callback_data.split('_')[-1]))

    await update.effective_message.reply_text(
        text='Вход в парадную откуда?',
        reply_markup=get_entrance_type_keyboard(advertisement_id=-1),
    )

    await update.effective_message.delete()

    # await edit_caption_or_text(
    #     context.user_data["effective_message"],
    #     get_appropriate_text(advertisement),
    # )

    return AddRoomDialogStates.ENTRANCE_TYPE


async def edit_entrance_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    data: DataToGather = context.user_data.get("data_to_gather")

    if callback_data.split('_')[-1] != 'skip':
        data.house_entrance_type = HouseEntranceType[callback_data.split('_')[-1]]

    await update.effective_message.delete()

    # await edit_caption_or_text(
    #     context.user_data["effective_message"],
    #     get_appropriate_text(advertisement),
    # )

    await update.effective_message.reply_text(
        text='Окна комнаты выходят куда?',
        reply_markup=get_view_type_keyboard(advertisement_id=-1),
    )

    return AddRoomDialogStates.WINDOWS_TYPE


async def edit_view_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    data: DataToGather = context.user_data.get("data_to_gather")

    if callback_data.split('_')[-1] != 'skip':
        data.view_type = [ViewType[callback_data.split('_')[-1]]]
        data.windows_count = 1

    await update.effective_message.delete()

    # await edit_caption_or_text(
    #     context.user_data["effective_message"],
    #     get_appropriate_text(advertisement),
    # )

    await update.effective_message.reply_text(
        text='Санузел в квартире какой?',
        reply_markup=get_toilet_type_keyboard(advertisement_id=-1),
    )

    return AddRoomDialogStates.TOILET_TYPE


async def edit_toilet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    data: DataToGather = context.user_data.get("data_to_gather")

    if callback_data.split('_')[-1] != 'skip':
        data.toilet_type = ToiletType[callback_data.split('_')[-1]]

    await update.effective_message.delete()

    # await edit_caption_or_text(
    #     context.user_data["effective_message"],
    #     get_appropriate_text(advertisement),
    # )

    message = await update.effective_message.reply_text(
        text='Введите информацию о комнатах (пропустить. -> /0)\n'
             'Пример: <i>5/28.6-Ж(2пенс МиЖ НОТ), 8/33.0-Н(М ПП), 9/24.9-Н(М ПИС)</i>\n'
             'Комнаты обязательно должны быть разделены запятой.',
        reply_markup=None,
        parse_mode='HTML'
    )

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.ROOMS_INFO


async def edit_rooms_info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text != '/0':
        search_pattern = r"(\d+)\/(\d+([.,]\d*)?)(.[^,]*\))"
        rooms_info = update.message.text

        matches = re.findall(search_pattern, rooms_info)

        advertisement_id = context.user_data.get("effective_advertisement_id")
        advertisement = await advertisement_service.get_advertisement(context.session, advertisement_id)
        await refresh_advertisement(context.session, advertisement)

        if len(matches) != advertisement.flat.number_of_rooms:
            message = await update.message.reply_text(
                "Количество введенных комнат отличается от количества комнат в квартире"
            )
            context.user_data["messages_to_delete"].extend([message, update.message])
            return

        rooms = []

        for match in matches:
            room_area = float(match[1].replace(',', '.'))
            room_plan_number = match[0]
            room_type = RoomTypeEnum.LIVING
            room_status = RoomStatusEnum.LIVING
            room_owners = [RoomOwnersEnum.MALE]
            room_refusal_status = RoomRefusalStatusEnum.NO
            room_occupants = [RoomOccupantsEnum.MALE]
            room_comment = match[3]

            room = Room(
                area=room_area,
                number_on_plan=room_plan_number,
                type=room_type,
                status=room_status,
                owners=room_owners,
                refusal_status=room_refusal_status,
                occupants=room_occupants,
                comment=room_comment,
                flat=advertisement.flat,
            )

            context.session.add(room)
            rooms.append(room)

        for el in advertisement.flat.rooms:
            context.session.delete(el)

        advertisement.flat.rooms = rooms

    data: DataToGather = context.user_data.get("data_to_gather")

    advertisement_id = context.user_data.get("effective_advertisement_id")
    advertisement = await advertisement_service.get_advertisement(context.session, advertisement_id)
    await refresh_advertisement(context.session, advertisement)

    # advertisement.flat.flat_number = data.flat_number if data.flat_number is not None else advertisement.flat.flat_number
    # advertisement.flat_cadastral_number = data.cadastral_number if data.cadastral_number is not None else advertisement.flat.cadastral_number
    # advertisement.flat.cadastral_number = data.cadastral_number if data.cadastral_number is not None else advertisement.flat.cadastral_number
    advertisement.flat.area = data.flat_area if data.flat_area is not None else advertisement.flat.area
    advertisement.flat.height = data.flat_height if data.flat_height is not None else advertisement.flat.height
    advertisement.flat.house.is_historical = data.is_historical if data.is_historical is not None else advertisement.flat.house.is_historical
    advertisement.flat.elevator_nearby = data.elevator_nearby if data.elevator_nearby is not None else advertisement.flat.elevator_nearby
    advertisement.flat.under_room_is_living = data.under_room_is_living if data.under_room_is_living is not None else advertisement.flat.under_room_is_living
    advertisement.flat.house.entrance_type = data.house_entrance_type if data.house_entrance_type is not None else advertisement.flat.house.entrance_type
    advertisement.flat.view_type = data.view_type if data.view_type != [] else advertisement.flat.view_type
    advertisement.flat.windows_count = data.windows_count if data.windows_count is not None else advertisement.flat.windows_count
    advertisement.flat.toilet_type = data.toilet_type if data.toilet_type is not None else advertisement.flat.toilet_type
    advertisement.flat.toilet_type = data.toilet_type if data.toilet_type is not None else advertisement.flat.toilet_type

    try:
        await context.session.commit()
    except Exception as e:
        await context.session.rollback()
        raise e

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    advertisement = await advertisement_service.get_advertisement(context.session, advertisement.id)
    await refresh_advertisement(context.session, advertisement)

    message = await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(advertisement),
        reply_markup=get_plan_inspection_keyboard(advertisement_id=advertisement.id),
    )

    del context.user_data['effective_advertisement_id']
    del context.user_data['effective_message']

    context.bot_data['last_message'] = message

    return ConversationHandler.END


async def cancel_edit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления информации о комнатах (данные не сохранены)',
    )
    await context.session.rollback()
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)
    return ConversationHandler.END
