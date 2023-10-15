from telegram import Update, Bot, Message, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from avito_parser import scrape_avito_room_ad,TooManyRequests, AvitoScrapingException
from database.types import RoomInfoCreate, DataToGather, RoomCreate, AdvertisementCreate, AdvertisementResponse
from database.enums import AdvertisementStatus, EntranceType, ViewType, ToiletType, RoomType
from bot.utils.dadata_repository import dadata
from bot.service import user as user_service
from bot.service import room as room_service
from bot.service import room_info as room_info_service
from bot.service import advertisement as advertisement_service


from typing import Optional
from logging import getLogger
import re

from .manage_data import AddRoomDialogStates, fill_first_room_template, fill_parsed_room_template
from .keyboards import (
    get_info_keyboard,
    get_plan_keyboard,
    get_phone_keyboard,
    get_entrance_type_keyboard,
    get_send_or_edit_keyboard,
    get_view_type_keyboard,
    get_toilet_type_keyboard,
    get_review_keyboard,
)


logger = getLogger(__name__)


async def update_message(bot: Bot, message_id: int, chat_id: int, data: DataToGather):
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
        context.user_data['advertisement_message'],
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
        result = await scrape_avito_room_ad(url)
    except TooManyRequests:
        message = await update.message.reply_text(
            'Авито блокирует подключения. Невозможно получить данные с сайте. Желаете добавить вручную?',
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

    context.user_data['data'] = data

    await update.message.delete()
    for message in context.user_data.get("messages_to_delete", []):
        await message.delete()

    message = await update.message.reply_text(
        text=fill_parsed_room_template(data),
        parse_mode='HTML',
        reply_markup=get_plan_keyboard(advertisement_id=0),
        disable_web_page_preview=True,
    )

    context.user_data['advertisement_message'] = message

    return AddRoomDialogStates.ADDITIONAL_INFO


async def start_change_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    message = await update.effective_message.reply_text(
        'Вставьте картинку с планом',
    )
    await context.user_data['advertisement_message'].edit_reply_markup(
        reply_markup=get_plan_keyboard(advertisement_id=0, is_active=True),
    )
    context.user_data.update({'message_to_delete': message})
    return AddRoomDialogStates.FLAT_PLAN


async def change_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    data = context.user_data["data"]
    data.plan_telegram_file_id = photo.file_id
    context.user_data["data"] = data

    await update.message.delete()
    await context.user_data['message_to_delete'].delete()
    await context.user_data['advertisement_message'].delete()
    message = await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=fill_parsed_room_template(data),
        parse_mode='HTML',
        reply_markup=get_phone_keyboard(advertisement_id=0),
    )
    context.user_data['advertisement_message'] = message
    return ConversationHandler.END


async def start_change_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    message = await update.effective_message.reply_text(
        'Введите телефон продавца и его имя и статус (пример: 8999999999 А-Петр)',
    )
    await context.user_data['advertisement_message'].edit_reply_markup(
        reply_markup=get_phone_keyboard(advertisement_id=0, is_active=True),
    )
    context.user_data["messages_to_delete"] = [message]
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

    data = context.user_data["data"]
    data.contact_phone = phone_number
    data.contact_name = contact_name
    data.contact_status = status
    context.user_data["data"] = data

    await edit_caption_or_text(
        context.user_data['advertisement_message'],
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
    await context.user_data['advertisement_message'].edit_reply_markup(
        reply_markup=get_info_keyboard(advertisement_id=0, is_active=True),
    )
    message = await update.effective_message.reply_text(
        'Номер квартиры (если нет данных -> /0)',
    )
    context.user_data["messages_to_delete"] = [message]
    return AddRoomDialogStates.FLAT_NUMBER


async def change_flat_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '/0':
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (если нет данных -> /0)',
        )
        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.KADASTR_NUMBER

    if not await validate_message_text(update, context, r'\d+([а-яА-Я]*)'):
        return

    data = context.user_data["data"]
    data.flat_number = update.message.text
    context.user_data["data"] = data

    address = dadata.get_clean_data(data.address + ' ' + data.flat_number)

    if not address.flat_cadnum:
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (если нет данных -> /0)',
        )
        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.KADASTR_NUMBER


    data.cadastral_number = address.flat_cadnum
    context.user_data["data"] = data

    message = await update.effective_message.reply_text(
        text='Высота потолка (если нет данных -> /0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.FLAT_HEIGHT


async def change_kadastr_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != '/0':
        if not await validate_message_text(update, context, r'\d{2}:\d{2}:\d{6,7}:\d{1,2}'):
            return

        data = context.user_data["data"]
        data.cadastral_number = update.message.text
        context.user_data["data"] = data

    message = await update.effective_message.reply_text(
        text='Высота потолка (если нет данных -> /0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.FLAT_HEIGHT


async def change_flat_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != '/0':
        if not await validate_message_text(update, context, r'\d+([.,]\d+)?'):
            return

        height = float(update.message.text.replace(',', '.'))

        data = context.user_data["data"]
        data.flat_height = height
        context.user_data["data"] = data

    message = await update.effective_message.reply_text(
        text='Площадь квартиры (если нет данных -> /0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.FLAT_AREA


async def change_flat_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != '/0':
        pattern = r'\d+([.,]\d+)?'

        if not await validate_message_text(update, context, pattern):
            return

        area = float(update.message.text.replace(',', '.'))

        data = context.user_data["data"]
        data.flat_area = area
        context.user_data["data"] = data

    message = await update.effective_message.reply_text(
        text='Дом является памятником? (да->1 нет->0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.HOUSE_IS_HISTORICAL


async def change_house_is_historical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'[01]'

    if not await validate_message_text(update, context, pattern):
        return

    data = context.user_data["data"]
    data.house_is_historical = bool(int(update.message.text))
    context.user_data["data"] = data

    message = await update.effective_message.reply_text(
        text='Есть лифт рядом в квартирой? (да->1 нет->0)',
    )
    context.user_data["messages_to_delete"] += [message, update.message]

    return AddRoomDialogStates.ELEVATOR_NEARBY


async def change_elevator_nearby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pattern = r'[01]'

    if not await validate_message_text(update, context, pattern):
        return

    data = context.user_data["data"]
    data.elevator_nearby = bool(int(update.message.text))
    context.user_data["data"] = data

    if data.flour == 2:
        message = await update.effective_message.reply_text(
            text='Помещение под квартирой жилое? (да->1 нет->0)',
        )
        context.user_data["messages_to_delete"] += [message, update.message]
        return AddRoomDialogStates.ROOM_UNDER
    else:
        data.room_under_is_living = True
        context.user_data["data"] = data
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

    data = context.user_data["data"]
    data.elevator_nearby = bool(int(update.message.text))
    context.user_data["data"] = data

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

        data = context.user_data["data"]
        data.entrance_type = entrance_type
        context.user_data["data"] = data

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

        data = context.user_data["data"]
        data.view_type = windows_type
        context.user_data["data"] = data

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

        data = context.user_data["data"]
        data.toilet_type = toilet_type
        context.user_data["data"] = data

    message = await update.effective_message.reply_text(
        text='Введите информацию о комнатах (если нет данных -> /0)\n'
             'пример: 5/28.6-Ж(2пенс МиЖ НОТ), 8/33.0-Н(М ПП), 9/24.9-Н(М ПИС)',
        reply_markup=None,
    )
    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.ROOMS_INFO


async def change_rooms_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != '/0':
        full_pattern = r"((\d+)/(\d+([.,]\d+)?)[\s-]([ЖН])\((.*)\))[.,]?"
        search_pattern = r"(\d+)/(\d+([.,]\d+)?)[\s-]([ЖН])\(([^)]*)\)[.,]?"
        rooms_info = update.message.text

        if not await validate_message_text(update, context, full_pattern):
            return

        matches = re.findall(search_pattern, rooms_info)

        data = context.user_data["data"]

        rooms = []

        for match in matches:
            room_plan_number = match[0]
            room_area = float(match[1].replace(',', '.'))
            room_status = RoomType(match[3])
            room_description = match[4]

            room = RoomInfoCreate(
                number=room_plan_number,
                area=room_area,
                status=room_status,
                description=room_description,
            )

            rooms.append(room)

        data.rooms_info = rooms
        context.user_data["data"] = data

    await update.message.delete()
    await delete_messages(context)

    if context.user_data.get('done'):
        await edit_caption_or_text(
            context.user_data['advertisement_message'],
            fill_first_room_template(context.user_data["data"]),
            reply_markup=get_send_or_edit_keyboard(advertisement_id=0),
        )
        await edit_caption_or_text(
            context.user_data['old_message'],
            fill_parsed_room_template(context.user_data['data']),
            reply_markup=None,
        )
    else:
        context.user_data['old_message'] = context.user_data['advertisement_message']
        await edit_caption_or_text(
            context.user_data['advertisement_message'],
            fill_parsed_room_template(context.user_data["data"]),
            reply_markup=None,
        )
        message = await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=context.user_data["data"].plan_telegram_file_id,
            caption=fill_first_room_template(context.user_data["data"]),
            parse_mode='HTML',
            reply_markup=get_send_or_edit_keyboard(advertisement_id=0),
        )
        context.user_data['advertisement_message'] = message
        context.user_data['done'] = True

    return ConversationHandler.END


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.effective_message.edit_reply_markup(reply_markup=None)

    data = context.user_data["data"]

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    # extract last 8 digits from cadastral number
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

    room = await room_service.create_room(session, room_create)

    await room_info_service.create_rooms_info(session, data.rooms_info, room)

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

    advertisement = await advertisement_service.create_advertisement(session, advertisement_create)

    admins = await user_service.get_admins(session)
    for admin in admins:
        if admin.id != update.effective_user.id:
            await context.bot.send_photo(
                chat_id=admin.id,
                photo=data.plan_telegram_file_id,
                caption=fill_first_room_template(data),
                reply_markup=get_review_keyboard(advertisement_id=advertisement.id),
                parse_mode='HTML',
            )

    # await context.bot.send_photo(
    #     chat_id=update.effective_chat.id,
    #     photo=context.user_data["data"].plan_telegram_file_id,
    #     caption=fill_second_room_template(context.user_data["data"]),
    #     parse_mode='HTML',
    # )
    return ConversationHandler.END


async def cancel_room_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления комнаты (данные не сохранены)',
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
    await bot.send_photo(
        chat_id=user_id,
        photo=data.plan_telegram_file_id,
        caption=fill_first_room_template(data),
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
