import pprint

from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes

from bot.handlers.rooms.manage_data import AddRoomDialogStates, get_data_by_advertisement, get_data_by_advertisement_id
from bot.handlers.rooms.handlers import (get_appropriate_text,
                                         update_message_and_delete_messages, edit_caption_or_text)
from bot.handlers.review.keyboards import get_plan_inspection_keyboard
from bot.service import advertisement as advertisement_service
from bot.service import room as room_service
from bot.service import room_info as room_info_service
from bot.utils.utils import delete_messages, delete_message_or_skip, validate_message_text, cadnum_to_id
from bot.utils.dadata_repository import dadata

from bot.handlers.rooms.keyboards import (
    get_house_is_historical_keyboard,
    get_entrance_type_keyboard,
    get_view_type_keyboard,
    get_toilet_type_keyboard,
    get_yes_or_no_keyboard,
)
from database.models import Advertisement, RoomInfo

from database.types import DataToGather, RoomInfoCreate
from database.enums import EntranceType, ViewType, ToiletType, RoomType

import re

from sqlalchemy.ext.asyncio import AsyncSession


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

    if not advertisement:
        await update.effective_message.reply_text(
            'Объявление не найдено',
        )
        return ConversationHandler.END

    await session.refresh(advertisement, attribute_names=['room'])

    advertisement.room.plan_telegram_file_id = photo.file_id
    await session.commit()

    data = await get_data_by_advertisement_id(session, advertisement_id)

    keyboard = get_plan_inspection_keyboard(advertisement_id=advertisement_id)

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=get_appropriate_text(data),
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

    advertisement.contact_phone = phone
    advertisement.contact_name = name
    advertisement.contact_status = letter

    await context.session.commit()
    await context.session.refresh(advertisement, attribute_names=['room'])

    data = await get_data_by_advertisement_id(context.session, advertisement_id)

    keyboard = get_plan_inspection_keyboard(advertisement_id=advertisement_id)

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=advertisement.room.plan_telegram_file_id,
        caption=get_appropriate_text(data),
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
        'Номер квартиры (пропустить -> /0)',
    )

    context.user_data["messages_to_delete"] = [message]
    context.user_data["effective_advertisement_id"] = advertisement_id
    advertisement = await advertisement_service.get_advertisement(context.session, advertisement_id)
    await context.session.refresh(advertisement, attribute_names=['room'])
    await context.session.refresh(advertisement.room, attribute_names=['rooms_info'])
    await context.session.refresh(advertisement, attribute_names=['added_by'])
    context.user_data["effective_advertisement"] = advertisement
    context.user_data["effective_message"] = update.effective_message

    data = DataToGather()
    context.user_data['effective_data'] = data

    return AddRoomDialogStates.FLAT_NUMBER


async def edit_flat_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if update.message.text == '/0':
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0) <a href="https://dadata.ru/suggestions/#address">Дадата</a>',
            parse_mode='HTML',
            disable_web_page_preview=True,
        )

        advertisement: Advertisement = context.user_data.get("effective_advertisement")

        data = await get_data_by_advertisement(advertisement)

        await update_message_and_delete_messages(update, context, data)

        context.user_data["messages_to_delete"].append(message)

        return AddRoomDialogStates.KADASTR_NUMBER

    if not await validate_message_text(update, context, r'\d+([а-яА-Я]*)'):
        return

    advertisement.room.flat_number = update.message.text
    context.user_data['effective_advertisement'] = advertisement
    data = await get_data_by_advertisement(context.user_data.get("effective_advertisement"))

    await update_message_and_delete_messages(update, context, data)

    address = dadata.get_clean_data(advertisement.room.address + 'литера А, кв' + advertisement.room.flat_number)
    if address.fias_level < 8:
        address = dadata.get_clean_data(advertisement.room.address + ',кв. ' + advertisement.room.flat_number)
        if address.fias_level < 8:
            address = None

    if not address or not address.flat_cadnum:
        pprint.pprint(address)
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0) <a href="https://dadata.ru/suggestions/#address">Дадата</a>',
            parse_mode='HTML',
            disable_web_page_preview=True,
        )
        context.user_data["messages_to_delete"] += [message]

        return AddRoomDialogStates.KADASTR_NUMBER

    message = await update.effective_message.reply_text(
        text=f'Кадастровый номер: {address.flat_cadnum}',
    )
    context.user_data["messages_to_delete"] += [message]

    if address.flat_cadnum and await room_service.get_room(context.session, cadnum_to_id(address.flat_cadnum)):
        message = await update.effective_message.reply_text(
            text='Квартира с таким кадастровым номером уже существует. '
                 'Проверьте номер или напишите /cancel, чтобы отменить добавление',
        )
        context.user_data["messages_to_delete"] += [message]
        return AddRoomDialogStates.KADASTR_NUMBER

    advertisement.room.cadnum = address.flat_cadnum
    advertisement.room.address = f'{address.street} {address.street_type} {address.house}'

    context.user_data['effective_advertisement'] = advertisement

    if not address.flat_area:
        message = await update.effective_message.reply_text(
            text='Площадь квартиры (пропустить -> /0)',
        )
        context.user_data["messages_to_delete"] += [message]

        return AddRoomDialogStates.FLAT_AREA

    message = await update.effective_message.reply_text(
        text=f'Площадь квартиры: {address.flat_area} м2',
    )
    context.user_data["messages_to_delete"] += [message]
    advertisement.room.flat_area = float(address.flat_area.replace(',', '.'))
    context.user_data['effective_advertisement'] = advertisement

    message = await update.effective_message.reply_text(
        text='Высота потолка (пропустить -> /0)',
    )

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.FLAT_HEIGHT


async def edit_cadnum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if update.message.text != '/0':
        if not validate_message_text(update, context, r'\d+:\d+:\d+:\d+'):
            return

        if await room_service.get_room(context.session, cadnum_to_id(update.message.text)):
            message = await update.effective_message.reply_text(
                text='Квартира с таким кадастровым номером уже существует. '
                     'Проверьте номер или напишите /cancel, чтобы отменить добавление',
            )
            context.user_data["messages_to_delete"] += [message, update.effective_message]

            return AddRoomDialogStates.KADASTR_NUMBER

        advertisement.room.cadastral_number = update.message.text
        context.user_data['effective_advertisement'] = advertisement

        address = dadata.get_clean_data_by_cadastral_number(update.message.text)

        if address and address.flat_area:
            message = await update.effective_message.reply_text(
                text=f'Площадь квартиры: {address.flat_area} м2',
            )
            context.user_data["messages_to_delete"] += [message]
            advertisement.room.flat_area = float(address.flat_area.replace(',', '.'))
            advertisement.room.address = f'{address.street} {address.street_type} {address.house}'
            context.user_data['effective_advertisement'] = advertisement

            message = await update.effective_message.reply_text(
                text='Высота потолка (пропустить -> /0)',
            )

            context.user_data["messages_to_delete"] += [message]

            return AddRoomDialogStates.FLAT_HEIGHT

    message = await update.effective_message.reply_text(
        text='Площадь квартиры (пропустить -> /0)',
    )

    data = await get_data_by_advertisement(advertisement)

    await update_message_and_delete_messages(update, context, data)

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.FLAT_AREA


async def edit_flat_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if update.message.text != '/0':
        if not validate_message_text(update, context, r'\d+([.,]\d+)?'):
            return

        advertisement.room.flat_area = float(update.message.text.replace(',', '.'))
        context.user_data['effective_advertisement'] = advertisement

    message = await update.effective_message.reply_text(
        text='Высота потолка (пропустить -> /0)',
    )

    data = await get_data_by_advertisement(advertisement)

    await update_message_and_delete_messages(update, context, data)

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.FLAT_HEIGHT


async def edit_flat_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if update.message.text != '/0':
        if not validate_message_text(update, context, r'\d+([.,]\d+)?'):
            return

        advertisement.room.flat_height = float(update.message.text.replace(',', '.'))
        context.user_data['effective_advertisement'] = advertisement

    await update.effective_message.reply_text(
        text='Дом является памятником?',
        reply_markup=get_house_is_historical_keyboard(-1),
    )

    data = await get_data_by_advertisement(advertisement)

    await update_message_and_delete_messages(update, context, data)

    return AddRoomDialogStates.HOUSE_IS_HISTORICAL


async def edit_house_is_historical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if callback_data.split('_')[-1] != 'skip':
        advertisement.room.house_is_historical = bool(int(callback_data.split('_')[-1]))
        context.user_data['effective_advertisement'] = advertisement

    await update.effective_message.reply_text(
        text='Есть лифт рядом с квартирой?',
        reply_markup=get_yes_or_no_keyboard(callback_pattern='is_elevator_nearby_'),
    )

    await update.effective_message.delete()

    data = await get_data_by_advertisement(advertisement)

    await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(data),
    )

    return AddRoomDialogStates.ELEVATOR_NEARBY


async def edit_elevator_nearby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if callback_data.split('_')[-1] != 'skip':
        advertisement.room.elevator_nearby = bool(int(callback_data.split('_')[-1]))
        context.user_data['effective_advertisement'] = advertisement

    await update.effective_message.delete()

    data = await get_data_by_advertisement(advertisement)

    await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(data),
    )

    if data.flour == 2:
        await update.effective_message.reply_text(
            text='Помещение под этой квартирой жилое?',
            reply_markup=get_yes_or_no_keyboard(callback_pattern='room_under_is_living_'),
        )

        return AddRoomDialogStates.ROOM_UNDER

    advertisement.room.under_room_is_living = True
    context.user_data['effective_advertisement'] = advertisement
    await update.effective_message.reply_text(
        text='Тип подъезда',
        reply_markup=get_entrance_type_keyboard(advertisement_id=-1),
    )

    return AddRoomDialogStates.ENTRANCE_TYPE


async def edit_room_under(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if callback_data.split('_')[-1] != 'skip':
        advertisement.room.under_room_is_living = bool(int(callback_data.split('_')[-1]))
        context.user_data['effective_advertisement'] = advertisement

    await update.effective_message.reply_text(
        text='Вход в парадную откуда?',
        reply_markup=get_entrance_type_keyboard(advertisement_id=-1),
    )

    await update.effective_message.delete()

    data = await get_data_by_advertisement(advertisement)

    await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(data),
    )

    return AddRoomDialogStates.ENTRANCE_TYPE


async def edit_entrance_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if callback_data.split('_')[-1] != 'skip':
        advertisement.room.entrance_type = EntranceType[callback_data.split('_')[-1]]
        context.user_data['effective_advertisement'] = advertisement

    await update.effective_message.delete()

    data = await get_data_by_advertisement(advertisement)

    await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(data),
    )

    await update.effective_message.reply_text(
        text='Окна комнаты выходят куда?',
        reply_markup=get_view_type_keyboard(advertisement_id=-1),
    )

    return AddRoomDialogStates.WINDOWS_TYPE


async def edit_view_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if callback_data.split('_')[-1] != 'skip':
        advertisement.room.view_type = ViewType[callback_data.split('_')[-1]]
        context.user_data['effective_advertisement'] = advertisement

    await update.effective_message.delete()

    data = await get_data_by_advertisement(advertisement)

    await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(data),
    )

    await update.effective_message.reply_text(
        text='Санузел',
        reply_markup=get_toilet_type_keyboard(advertisement_id=-1),
    )

    return AddRoomDialogStates.TOILET_TYPE


async def edit_toilet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    callback_data = update.callback_query.data

    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if callback_data.split('_')[-1] != 'skip':
        advertisement.room.toilet_type = ToiletType[callback_data.split('_')[-1]]
        context.user_data['effective_advertisement'] = advertisement

    await update.effective_message.delete()

    data = await get_data_by_advertisement(advertisement)

    await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(data),
    )

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
    advertisement: Advertisement = context.user_data.get("effective_advertisement")

    if update.message.text != '/0':
        search_pattern = r"(\d+)\/(\d+([.,]\d*)?)(.[^,]*\))"
        rooms_info = update.message.text

        matches = re.findall(search_pattern, rooms_info)

        if len(matches) != advertisement.room.number_of_rooms_in_flat:
            message = await update.message.reply_text(
                "Количество введенных комнат отличается от количества комнат в квартире"
            )
            context.user_data["messages_to_delete"].extend([message, update.message])
            return

        rooms = []

        for match in matches:
            room_plan_number = match[0]
            room_area = float(match[1].replace(',', '.'))
            room_status = RoomType.FOR_RENT
            room_description = match[3]

            room = RoomInfoCreate(
                number=room_plan_number,
                area=room_area,
                status=room_status,
                description=room_description,
                main_room_id=advertisement.room.id,
            )

            rooms.append(room)

        await room_info_service.update_room_info(context.session, advertisement.room.id, rooms)

        advertisement = await advertisement_service.get_advertisement(context.session, advertisement.id)

        await context.session.refresh(advertisement, attribute_names=['room'])
        await context.session.refresh(advertisement.room, attribute_names=['rooms_info'])

    data = await get_data_by_advertisement(advertisement)

    await update_message_and_delete_messages(update, context, data)

    advertisement_id = context.user_data.get("effective_advertisement_id")

    await context.session.commit()

    await edit_caption_or_text(
        context.user_data["effective_message"],
        get_appropriate_text(data),
        reply_markup=get_plan_inspection_keyboard(advertisement_id=advertisement_id),
    )

    del context.user_data['effective_advertisement_id']
    del context.user_data['effective_data']
    del context.user_data['effective_message']
    del context.user_data['effective_advertisement']

    await delete_messages(context)

    return ConversationHandler.END


async def cancel_edit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления информации о комнатах (данные не сохранены)',
    )
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)
    return ConversationHandler.END
