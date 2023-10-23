import asyncio
import pprint

from telegram import Update, Bot, Message, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from avito_parser import scrape_avito_room_ad,TooManyRequests, AvitoScrapingException
from database.types import RoomInfoCreate, DataToGather, RoomCreate, AdvertisementCreate, AdvertisementResponse
from database.enums import AdvertisementStatus, EntranceType, ViewType, ToiletType, RoomType
from bot.utils.utils import cadnum_to_id
from bot.utils.dadata_repository import dadata
from bot.service import user as user_service
from bot.service import room as room_service
from bot.service import room_info as room_info_service
from bot.service import advertisement as advertisement_service

from pydantic import ValidationError

from typing import Optional
from logging import getLogger
import re

from .manage_data import (
    AddRoomDialogStates,
    CalculateRoomDialogStates,
    fill_first_room_template,
    fill_parsed_room_template,
    fill_data_from_advertisement_template,
)
from .static_text import DISPATCHER_USERNAME_TEMPLATE
from .keyboards import (
    get_info_keyboard,
    get_plan_keyboard,
    get_phone_keyboard,
    get_entrance_type_keyboard,
    get_send_or_edit_keyboard,
    get_view_type_keyboard,
    get_toilet_type_keyboard,
    get_review_keyboard,
    get_yes_or_no_keyboard,
)


logger = getLogger(__name__)


async def update_message_first_template(bot: Bot, message_id: int, chat_id: int, data: DataToGather):
    await bot.edit_message_text(
        text=fill_first_room_template(data),
        chat_id=chat_id,
        message_id=message_id,
        parse_mode='HTML',
        disable_web_page_preview=True,
    )


async def edit_caption_or_text(message: Message, new_text: str, reply_markup: Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup] = None):
    try:
        if message.caption:
            await message.edit_caption(
                caption=new_text,
                parse_mode='HTML',
                reply_markup=reply_markup,
            )
        else:
            await message.edit_text(
                text=new_text,
                parse_mode='HTML',
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
    except Exception as e:
        logger.error(e)


async def validate_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE, pattern: str) -> bool:
    if not re.fullmatch(pattern, update.message.text):
        message = await update.message.reply_text(
            'Неправильный формат ввода',
        )
        context.user_data["messages_to_delete"].extend([message, update.message])
        return False
    return True


async def update_message_and_delete_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_caption_or_text(
        context.user_data['effective_message_id'],
        fill_first_room_template(context.user_data["data"]),
    )
    await update.message.delete()
    await delete_messages(context)


async def delete_messages(context: ContextTypes.DEFAULT_TYPE):
    for message in context.user_data.get("messages_to_delete", []):
        await message.delete()
    context.user_data["messages_to_delete"] = []


async def start_adding_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text(
        'Введите ссылку на объявление',
    )
    context.user_data['messages_to_delete'] = [update.message, message]
    return AddRoomDialogStates.ROOM_URL


async def add_room_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    avito_rooms_link_pattern = r'https?://(www|m)\.avito\.ru/.*?/komnaty/.*'
    url = update.message.text

    if not re.match(avito_rooms_link_pattern, url):
        message = await update.message.reply_text(
            'Ссылка не подходит. Исправьте и отправьте еще раз.',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return

    if 'm.avito.ru' in url:
        url = url.replace('m.avito.ru', 'www.avito.ru')

    try:
        session = context.session
    except AttributeError:
        raise RuntimeError('Session is not in context')

    if await advertisement_service.get_advertisement_by_url(session, url):
        message = await update.message.reply_text(
            'Объявление с такой ссылкой уже существует. Отправьте другую ссылку или напишите /cancel',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return

    try:
        result = await scrape_avito_room_ad(url)
    except TooManyRequests:
        message = await update.message.reply_text(
            'Авито блокирует подключения. Невозможно получить данные с сайте.',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return
    except AvitoScrapingException:
        message = await update.message.reply_text(
            'Не удалось получить информацию по ссылке, попробуйте еще раз',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return

    data = DataToGather(
        url=url,
        price=result.price,
        description=result.description,
        added_by_id=update.effective_user.id,
        room_area=result.room_area,
        number_of_rooms_in_flat=result.number_of_rooms_in_flat,
        flour=result.flour,
        flours_in_building=result.flours_in_building,
        address=result.address,
    )

    await update.message.delete()
    for message in context.user_data.get("messages_to_delete", []):
        await message.delete()

    message = await update.message.reply_text(
        text=fill_parsed_room_template(data),
        parse_mode='HTML',
        reply_markup=get_plan_keyboard(advertisement_id=0),
        disable_web_page_preview=True,
    )

    context.user_data[message.id] = data

    return ConversationHandler.END


async def start_change_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    message = await update.effective_message.reply_text(
        'Вставьте картинку с планом',
    )
    await update.effective_message.edit_reply_markup(
        reply_markup=get_plan_keyboard(advertisement_id=0, is_active=True),
    )
    context.user_data.update({'message_to_delete': message})
    context.user_data.update({'effective_message_id': update.effective_message.id})
    return AddRoomDialogStates.FLAT_PLAN


async def change_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data.plan_telegram_file_id = photo.file_id

    await update.message.delete()
    await context.user_data['message_to_delete'].delete()
    await context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['effective_message_id'],
    )
    message = await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=fill_parsed_room_template(data),
        parse_mode='HTML',
        reply_markup=get_phone_keyboard(advertisement_id=0),
    )
    del context.user_data[effective_message_id]
    context.user_data[message.id] = data
    return ConversationHandler.END


async def start_change_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    message = await update.effective_message.reply_text(
        'Введите телефон продавца и его имя и статус\nПример: <i>8999999999 А-Петр</i>',
        parse_mode='HTML',
    )
    await update.effective_message.edit_reply_markup(
        reply_markup=get_phone_keyboard(advertisement_id=0, is_active=True),
    )
    context.user_data["messages_to_delete"] = [message]
    context.user_data.update({'effective_message_id': update.effective_message.id})
    context.user_data.update({'effective_message': update.effective_message})
    return AddRoomDialogStates.CONTACT_PHONE


async def change_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_string = update.message.text

    pattern = r'((\+7|8)?(\d{10}))[\s-]*([АВСХавсх])[\s-](.*)'

    # Use re.search() to find matches
    match = re.search(pattern, input_string)

    if not match:
        message = await update.message.reply_text(
            'Неправильный формат ввода',
        )
        context.user_data["messages_to_delete"].extend([message, update.message])
        return

    phone_number = match.group(1)
    status = match.group(4).upper()
    contact_name = match.group(5).capitalize()

    if status in ['В', 'Х']:
        status = 'С'

    if phone_number.startswith('+7'):
        phone_number = phone_number[2:]

    if phone_number.startswith('9'):
        phone_number = '8' + phone_number

    effective_message_id: int = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data.contact_phone = phone_number
    data.contact_name = contact_name
    data.contact_status = status
    context.user_data[effective_message_id] = data

    await edit_caption_or_text(
        context.user_data['effective_message'],
        fill_parsed_room_template(data),
        get_info_keyboard(advertisement_id=0),
    )
    await update.message.delete()
    for message in context.user_data.get("messages_to_delete", []):
        await message.delete()
    context.user_data["messages_to_delete"] = []
    return ConversationHandler.END


async def start_change_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.effective_message.edit_reply_markup(
        reply_markup=get_info_keyboard(advertisement_id=0, is_active=True),
    )
    message = await update.effective_message.reply_text(
        'Номер квартиры (пропустить -> /0)',
    )
    context.user_data["messages_to_delete"] = [message]
    context.user_data["effective_message_id"] = update.effective_message.id
    context.user_data["effective_message"] = update.effective_message
    return AddRoomDialogStates.FLAT_NUMBER


async def change_flat_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '/0':
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0)',
        )
        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.KADASTR_NUMBER

    if not await validate_message_text(update, context, r'\d+([а-яА-Я]*)'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data.flat_number = update.message.text

    address = dadata.get_clean_data(data.address + 'литера А, кв' + data.flat_number)
    if address.fias_level < 8:
        address = dadata.get_clean_data(data.address + ',кв. ' + data.flat_number)
        if address.fias_level < 8:
            address = None

    if not address or not address.flat_cadnum:
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0)',
        )
        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.KADASTR_NUMBER
    else:
        message = await update.effective_message.reply_text(
            text=f'Кадастровый номер: {address.flat_cadnum}',
        )
        context.user_data["messages_to_delete"] += [message]

    if address.flat_cadnum and await room_service.get_room(context.session, cadnum_to_id(address.flat_cadnum)):
        message = await update.effective_message.reply_text(
            text='Квартира с таким кадастровым номером уже существует. '
                 'Проверьте номер или напишите /cancel, чтобы отменить добавление',
        )
        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.FLAT_NUMBER

    data.cadastral_number = address.flat_cadnum
    data.address = f'{address.street} {address.street_type} {address.house}'
    context.user_data[effective_message_id] = data

    if address.flat_area:
        message = await update.effective_message.reply_text(
            text=f'Площадь квартиры: {address.flat_area} м2',
        )
        context.user_data["messages_to_delete"] += [message]
        data.flat_area = float(address.flat_area.replace(',', '.'))
        context.user_data[effective_message_id] = data

        message = await update.effective_message.reply_text(
            text='Высота потолка (пропустить -> /0)',
        )

        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.FLAT_HEIGHT
    else:
        message = await update.effective_message.reply_text(
            text='Площадь квартиры (пропустить -> /0)',
        )
        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.FLAT_AREA


async def change_kadastr_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if update.message.text != '/0':
        if not await validate_message_text(update, context, r'[\d:]*'):
            return

        if await room_service.get_room(context.session, cadnum_to_id(update.message.text)):
            message = await update.effective_message.reply_text(
                text='Квартира с таким кадастровым номером уже существует. '
                     'Проверьте номер или напишите /cancel, чтобы отменить добавление',
            )
            context.user_data["messages_to_delete"] += [message, update.message]

            return AddRoomDialogStates.FLAT_NUMBER

        data.cadastral_number = update.message.text
        context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Площадь квартиры (пропустить -> /0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.FLAT_AREA


async def change_flat_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if update.message.text != '/0':
        pattern = r'\d+([.,]\d+)?'

        if not await validate_message_text(update, context, pattern):
            return

        area = float(update.message.text.replace(',', '.'))

        data.flat_area = area
        context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Высота потолка (пропустить -> /0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.FLAT_HEIGHT


async def change_flat_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if update.message.text != '/0':
        if not await validate_message_text(update, context, r'\d+([.,]\d+)?'):
            return

        height = float(update.message.text.replace(',', '.'))

        data.flat_height = height
        context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Дом является памятником? (да->1 нет->0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.HOUSE_IS_HISTORICAL


async def change_house_is_historical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'[01]'

    if not await validate_message_text(update, context, pattern):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data.house_is_historical = bool(int(update.message.text))
    context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Есть лифт рядом в квартирой? (да->1 нет->0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.ELEVATOR_NEARBY


async def change_elevator_nearby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'[01]'

    if not await validate_message_text(update, context, pattern):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data.elevator_nearby = bool(int(update.message.text))
    context.user_data[effective_message_id] = data

    if data.flour == 2:
        message = await update.effective_message.reply_text(
            text='Помещение под этой квартирой: квартира - 1, нежилое - 0',
        )
        context.user_data["messages_to_delete"] += [message, update.message]
        return AddRoomDialogStates.ROOM_UNDER
    else:
        data.room_under_is_living = True
        context.user_data[effective_message_id] = data
        message = await update.effective_message.reply_text(
            text='Тип подъезда',
            reply_markup=get_entrance_type_keyboard(advertisement_id=0),
        )
        context.user_data["messages_to_delete"] += [message, update.message]
        return AddRoomDialogStates.ENTRANCE_TYPE


async def change_room_under(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'[01]'

    if not await validate_message_text(update, context, pattern):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data.room_under_is_living = bool(int(update.message.text))
    context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Вход в парадную откуда?',
        reply_markup=get_entrance_type_keyboard(advertisement_id=0),
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.ENTRANCE_TYPE


async def change_entrance_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.effective_message.edit_reply_markup(reply_markup=None)

    call_back_data = update.callback_query.data

    if call_back_data.split('_')[-1] != 'skip':
        entrance_type = EntranceType[call_back_data.split('_')[-1]]

        effective_message_id = context.user_data['effective_message_id']
        data = context.user_data[effective_message_id]
        data.entrance_type = entrance_type
        context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Окна комнаты выходят куда?',
        reply_markup=get_view_type_keyboard(advertisement_id=0),
    )
    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.WINDOWS_TYPE


async def change_view_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.effective_message.edit_reply_markup(reply_markup=None)

    call_back_data = update.callback_query.data

    if call_back_data.split('_')[-1] != 'skip':
        windows_type = ViewType[call_back_data.split('_')[-1]]

        effective_message_id = context.user_data['effective_message_id']
        data = context.user_data[effective_message_id]
        data.view_type = windows_type
        context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Санузел в квартире какой?',
        reply_markup=get_toilet_type_keyboard(advertisement_id=0),
    )
    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.TOILET_TYPE


async def change_toilet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.effective_message.edit_reply_markup(reply_markup=None)

    call_back_data = update.callback_query.data

    if call_back_data.split('_')[-1] != 'skip':
        toilet_type = ToiletType[call_back_data.split('_')[-1]]

        effective_message_id = context.user_data['effective_message_id']
        data = context.user_data[effective_message_id]
        data.toilet_type = toilet_type
        context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Введите информацию о комнатах (пропустить. -> /0)\n'
             'Пример: <i>5/28.6-Ж(2пенс МиЖ НОТ), 8/33.0-Н(М ПП), 9/24.9-Н(М ПИС)</i>',
        reply_markup=None,
        parse_mode='HTML'
    )

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.ROOMS_INFO


async def change_rooms_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if update.message.text != '/0':
        full_pattern = r"((\d+)/(\d+([.,]\d+)?)[\s-]?([ЖНСРжнср\s])\((.*)\))[.,]?"
        search_pattern = r"(\d+)/(\d+([.,]\d+)?)[\s-]?([ЖНСРжнср\s])\(([^)]*)\)[.,]?"
        rooms_info = update.message.text

        if not await validate_message_text(update, context, full_pattern):
            return

        matches = re.findall(search_pattern, rooms_info)

        if len(matches) != data.number_of_rooms_in_flat:
            message = await update.message.reply_text(
                "Количество введенных комнат отличается от количетсва комнат в квартире"
            )
            context.user_data["messages_to_delete"].extend([message, update.message])
            return

        rooms = []

        for match in matches:
            room_plan_number = match[0]
            room_area = float(match[1].replace(',', '.'))
            room_status = RoomType(match[3].upper()) if match[3] else None
            room_description = match[4]

            room = RoomInfoCreate(
                number=room_plan_number,
                area=room_area,
                status=room_status,
                description=room_description,
            )

            rooms.append(room)

        data.rooms_info = rooms
        context.user_data[effective_message_id] = data

    await update.message.delete()
    await delete_messages(context)

    await edit_caption_or_text(
        context.user_data['effective_message'],
        fill_first_room_template(data),
        reply_markup=get_send_or_edit_keyboard(advertisement_id=0),
    )

    del context.user_data['effective_message_id']

    return ConversationHandler.END


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pprint.pprint(context.user_data)
    data = context.user_data[update.effective_message.id]

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    try:
        room_id = int(data.cadastral_number.replace(':', '')[-8:])
        room_create = RoomCreate(
            id=room_id,
            room_area=data.room_area,
            flat_area=data.flat_area,
            number_of_rooms_in_flat=data.number_of_rooms_in_flat,
            flour=data.flour,
            flours_in_building=data.flours_in_building,
            address=data.address,
            plan_telegram_file_id=data.plan_telegram_file_id,
            flat_number=data.flat_number,
            flat_height=data.flat_height,
            cadastral_number=data.cadastral_number,
            house_is_historical=data.house_is_historical,
            elevator_nearby=data.elevator_nearby,
            entrance_type=data.entrance_type,
            view_type=data.view_type,
            toilet_type=data.toilet_type,
            under_room_is_living=data.room_under_is_living,
        )

    except (ValidationError, AttributeError) as e:
        logger.error(e)
        await update.callback_query.answer(
            text='Заполните все поля',
            show_alert=True,
        )
        return

    try:
        room = await room_service.create_room(session, room_create)
    except ValueError as e:
        logger.error(e)
        await update.callback_query.answer(
            text='Квартира с таким кадастровым номером уже существует',
            show_alert=True,
        )
        return

    if not data.rooms_info:
        await update.callback_query.answer(
            text='Заполните все поля',
            show_alert=True,
        )
        return

    await room_info_service.create_rooms_info(session, data.rooms_info, room)

    try:
        advertisement_create = AdvertisementCreate(
            url=data.url,
            price=data.price,
            contact_phone=data.contact_phone,
            contact_status=data.contact_status,
            contact_name=data.contact_name,
            description=data.description,

            room_id=room.id,

            added_by_id=update.effective_user.id,
        )
    except ValidationError as e:
        logger.error(e)
        await update.callback_query.answer(
            text='Заполните все поля',
            show_alert=True,
        )
        return

    advertisement = await advertisement_service.create_advertisement(session, advertisement_create)

    await session.commit()

    await update.callback_query.answer(
        text='Объявление добавлено',
        show_alert=True,
    )

    text = fill_first_room_template(data)
    if advertisement.added_by:
        text += '\n' + DISPATCHER_USERNAME_TEMPLATE.format(
            username=advertisement.added_by.username,
        )

    admins = await user_service.get_admins(session)
    for admin in admins:
        if admin.id != update.effective_user.id:
            await context.bot.send_photo(
                chat_id=admin.id,
                photo=data.plan_telegram_file_id,
                caption=text,
                reply_markup=get_review_keyboard(advertisement_id=advertisement.id),
                parse_mode='HTML',
            )

    await update.effective_message.delete()

    del context.user_data[update.effective_message.id]

    return ConversationHandler.END


async def cancel_room_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления комнаты (данные не сохранены)',
    )
    await delete_messages(context)
    await update.message.delete()
    await context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['effective_message_id'],
    )
    return ConversationHandler.END


async def cancel_plan_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления план (данные не сохранены)',
    )
    return ConversationHandler.END


async def cancel_phone_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления телефона (данные не сохранены)',
    )
    return ConversationHandler.END


async def cancel_info_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления информации (данные не сохранены)',
    )
    return ConversationHandler.END


async def send_advertisement(session, bot: Bot, advertisement_id: int, user_id: int):
    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
    await session.refresh(advertisement.room, attribute_names=["rooms_info"])
    advertisement = AdvertisementResponse.model_validate(advertisement)

    data = DataToGather(
        **advertisement.model_dump(),
        **advertisement.room.model_dump(),
    )

    text = fill_first_room_template(data)
    if advertisement.added_by:
        text += '\n' + DISPATCHER_USERNAME_TEMPLATE.format(
            username=advertisement.added_by.username,
        )

    await bot.send_photo(
        chat_id=user_id,
        photo=data.plan_telegram_file_id,
        caption=text,
        parse_mode='HTML',
    )


async def view_advertisement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

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
        await advertisement_service.update_advertisement_status(
            session,
            advertisement_id,
            status,
            update.effective_user.id,
        )

        if status == AdvertisementStatus.VIEWED:
            await update.effective_message.reply_text(
                'Объявление помечено как хорошее',
            )

            for user in await user_service.get_dispatchers(session):
                await send_advertisement(session, context.bot, advertisement_id, user.id)
        elif status == AdvertisementStatus.CANCELED:
            await update.effective_message.reply_text(
                'Объявление помечено как плохое'
            )
    # await update.effective_message.edit_reply_markup(reply_markup=None)
    await delete_messages(context)


async def show_data_from_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get(update.effective_message.id)

    if not data:
        await update.callback_query.answer(
            text='К сожалению данные для этого сообщения потерялись',
            show_alert=True,
        )

    await update.callback_query.answer(
        text=fill_data_from_advertisement_template(data),
        show_alert=True,
    )


async def calculate_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get(update.effective_message.id):
        await update.callback_query.answer()
        data = update.callback_query.data
        ad_id = int(data.split('_')[-1])
        context.user_data[update.effective_message.id] = {'ad_id': ad_id}

        message = await update.effective_message.reply_text(
            'Введите цену за квадратный метр',
        )

        context.user_data["messages_to_delete"] = [message]
        context.user_data['effective_message_id'] = update.effective_message.id

        return CalculateRoomDialogStates.PRICE_PER_METER
    else:
        data = context.user_data[update.effective_message.id]

        try:
            session = context.session
        except AttributeError:
            raise Exception('Session is not in context')

        advertisement = await advertisement_service.get_advertisement(session, data.get('ad_id'))

        await session.refresh(advertisement.room, attribute_names=["rooms_info"])

        advertisement = AdvertisementResponse.model_validate(advertisement)

        #Цена кв-ры и комиссия АН: (165*112,6)=>18579*0,1=1858
# Маржа ЖкОП минус комиссия на 1м2 (МБК на1м2): (112.6-86.5)=>26.1*165=>4306-1858=>2448/86,5=>28
# Цена доли: 165*33,0=5445 / Доходность инвестора % годовых (срок 6 мес): (28/165)*100*2=>34

        price_per_meter = data.get('price_per_meter')
        agent_commission = data.get('agent_commission')

        if not price_per_meter or not agent_commission:
            await update.callback_query.answer(
                'Заполните все поля',
                show_alert=True,
            )
            return

        flat_price = price_per_meter * advertisement.room.flat_area
        agent_commission_price = flat_price * agent_commission / 100
        total_living_area = sum([room.area for room in advertisement.room.rooms_info])
        non_living_area = advertisement.room.flat_area - total_living_area
        non_living_price = non_living_area * price_per_meter
        something = non_living_price - agent_commission_price
        something_per_meter = something / total_living_area

        text = f'Цена квартиры: {flat_price}\n' \
                f'Комиссия агента: {agent_commission_price}\n\n'

        for el in advertisement.room.rooms_info:
            text += f'Комната {el.number} - {el.area} м2\n'\
                    f'Цена: {el.area * price_per_meter}'

        text += '\n' + f'Доходность инвестора % годовых (срок 6 мес): {(something_per_meter / price_per_meter) * 100 * 2}'

        await update.callback_query.answer()

        message = await update.effective_message.reply_text(
            text=text,
        )

        context.user_data["messages_to_delete"] += [message]

        return ConversationHandler.END


async def process_price_per_meter(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_message_text(update, context, r'\d+([.,]\d+)?'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data['price_per_meter'] = float(update.message.text.replace(',', '.'))

    message = await update.effective_message.reply_text(
        'Введите комиссию агента',
    )

    context.user_data["messages_to_delete"] += [message, update.message]

    return CalculateRoomDialogStates.AGENT_COMMISSION


async def process_agent_commission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_message_text(update, context, r'\d+([.,]\d+)?'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data['agent_commission'] = float(update.message.text.replace(',', '.'))

    await update.message.delete()
    await delete_messages(context)

    return ConversationHandler.END


async def cancel_calculating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.effective_message.reply_text(
        'Отмена расчета (данные не сохранены)',
    )
    await delete_messages(context)
    await update.message.delete()
    await asyncio.sleep(5)
    await message.delete()
    return ConversationHandler.END
