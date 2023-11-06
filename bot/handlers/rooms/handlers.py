import asyncio
import pprint

from telegram import Update, Bot, Message, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from avito_parser import scrape_avito_room_ad, TooManyRequests, AvitoScrapingException
from database.types import RoomInfoCreate, DataToGather, RoomCreate, AdvertisementCreate, AdvertisementResponse
from database.enums import AdvertisementStatus, EntranceType, ViewType, ToiletType, RoomType
from bot.utils.utils import cadnum_to_id, validate_message_text
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
from .static_text import DISPATCHER_USERNAME_TEMPLATE, CALCULATING_RESULT_TEMPLATE
from .keyboards import (
    get_ad_editing_keyboard,
    get_entrance_type_keyboard,
    get_send_or_edit_keyboard,
    get_view_type_keyboard,
    get_toilet_type_keyboard,
    get_review_keyboard,
    get_yes_or_no_keyboard,
    get_calculate_keyboard,
    get_delete_keyboard,
    get_house_is_historical_keyboard,
    get_plan_inspection_keyboard,
)


logger = getLogger(__name__)


def what_is_filled(data: DataToGather) -> (bool, bool, bool):
    plan_is_filled = bool(data.plan_telegram_file_id)
    phone_is_filled = bool(data.contact_phone)
    info_is_filled = all(
        [
            data.flat_number,
            data.cadastral_number,
            data.room_area,
            data.flours_in_building,
            data.address,
            data.rooms_info,
            data.flat_area,
            data.room_under_is_living is not None,
            data.flat_height,
            data.house_is_historical is not None,
            data.elevator_nearby is not None,
            data.entrance_type,
            data.view_type,
            data.toilet_type,
        ]
    )
    return plan_is_filled, phone_is_filled, info_is_filled


def get_appropriate_text(data: DataToGather) -> str:
    if any(
            [
                data.flat_number,
                data.cadastral_number,
                data.room_area,
                data.flours_in_building,
                data.address,
                data.rooms_info,
                data.flat_area,
                data.room_under_is_living is not None,
                data.flat_height,
                data.house_is_historical is not None,
                data.elevator_nearby is not None,
                data.entrance_type,
                data.view_type,
                data.toilet_type,
            ]
    ):
        return fill_first_room_template(data)
    else:
        return fill_parsed_room_template(data)


def get_appropriate_keyboard(advertisement_id: int, data: DataToGather) -> InlineKeyboardMarkup:
    plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(data)
    if all([plan_is_filled, phone_is_filled, info_is_filled]):
        return get_send_or_edit_keyboard(advertisement_id)
    else:
        return get_ad_editing_keyboard(
            advertisement_id=advertisement_id,
            plan_is_filled=plan_is_filled,
            phone_is_filled=phone_is_filled,
            info_is_filled=info_is_filled,
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


async def update_message_and_delete_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, data: DataToGather):
    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
    )
    await update.message.delete()
    await delete_messages(context)


async def delete_messages(context: ContextTypes.DEFAULT_TYPE):
    for message in context.user_data.get("messages_to_delete", []):
        try:
            await message.delete()
        except Exception as e:
            logger.error(e)
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
    except Exception as e:
        message = await update.message.reply_text(
            'Неизвестная ошибка. Напишите /cancel, чтобы отменить добавление',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        raise e

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
        text=get_appropriate_text(data),
        parse_mode='HTML',
        reply_markup=get_ad_editing_keyboard(advertisement_id=0),
        disable_web_page_preview=True,
    )

    context.user_data[message.id] = data

    return ConversationHandler.END


async def start_change_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    message = await update.effective_message.reply_text(
        'Вставьте картинку с планом',
    )
    plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(context.user_data[update.effective_message.id])
    await update.effective_message.edit_reply_markup(
        reply_markup=get_ad_editing_keyboard(
            advertisement_id=0,
            plan_is_active=True,
            phone_is_filled=phone_is_filled,
            info_is_filled=info_is_filled,
        ),
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

    keyboard = get_appropriate_keyboard(advertisement_id=0, data=data)

    message = await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=get_appropriate_text(data),
        parse_mode='HTML',
        reply_markup=keyboard,
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
    plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(context.user_data[update.effective_message.id])
    await update.effective_message.edit_reply_markup(
        reply_markup=get_ad_editing_keyboard(
            advertisement_id=0,
            plan_is_filled=plan_is_filled,
            phone_is_active=True,
            info_is_filled=info_is_filled,
        ),
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

    keyboard = get_appropriate_keyboard(advertisement_id=0, data=data)

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
        keyboard,
    )
    await update.message.delete()
    for message in context.user_data.get("messages_to_delete", []):
        await message.delete()
    context.user_data["messages_to_delete"] = []
    return ConversationHandler.END


async def start_change_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(context.user_data[update.effective_message.id])
    await update.effective_message.edit_reply_markup(
        reply_markup=get_ad_editing_keyboard(
            advertisement_id=0,
            plan_is_filled=plan_is_filled,
            phone_is_filled=phone_is_filled,
            info_is_active=True,
        ),
    )
    message = await update.effective_message.reply_text(
        'Номер квартиры (пропустить -> /0)',
    )
    context.user_data["messages_to_delete"] = [message]
    context.user_data["effective_message_id"] = update.effective_message.id
    context.user_data["effective_message"] = update.effective_message
    return AddRoomDialogStates.FLAT_NUMBER


async def change_flat_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if update.message.text == '/0':
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0) <a href="https://dadata.ru/suggestions/#address">Дадата</a>',
            parse_mode='HTML',
            disable_web_page_preview=True,
        )

        await update_message_and_delete_messages(update, context, data)

        context.user_data["messages_to_delete"] += [message]

        return AddRoomDialogStates.KADASTR_NUMBER

    if not await validate_message_text(update, context, r'\d+([а-яА-Я]*)'):
        return

    data.flat_number = update.message.text

    await update_message_and_delete_messages(update, context, data)

    address = dadata.get_clean_data(data.address + 'литера А, кв' + data.flat_number)
    if address.fias_level < 8:
        address = dadata.get_clean_data(data.address + ',кв. ' + data.flat_number)
        if address.fias_level < 8:
            address = None

    if not address or not address.flat_cadnum:
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0) <a href="https://dadata.ru/suggestions/#address">Дадата</a>',
            parse_mode='HTML',
            disable_web_page_preview=True,
        )
        context.user_data["messages_to_delete"] += [message]

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
        context.user_data["messages_to_delete"] += [message]

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

        context.user_data["messages_to_delete"] += [message]

        return AddRoomDialogStates.FLAT_HEIGHT
    else:
        message = await update.effective_message.reply_text(
            text='Площадь квартиры (пропустить -> /0)',
        )
        context.user_data["messages_to_delete"] += [message]

        return AddRoomDialogStates.FLAT_AREA


async def change_cadastral_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        address = dadata.get_clean_data_by_cadastral_number(update.message.text)

        print(address.flat_area, address.flat_cadnum)
        print(address.flat_area, address.flat_cadnum)

        if address and address.flat_area:
            message = await update.effective_message.reply_text(
                text=f'Площадь квартиры: {address.flat_area} м2',
            )
            context.user_data["messages_to_delete"] += [message]
            data.flat_area = float(address.flat_area.replace(',', '.'))
            data.address = f'{address.street} {address.street_type} {address.house}'
            context.user_data[effective_message_id] = data

            message = await update.effective_message.reply_text(
                text='Высота потолка (пропустить -> /0)',
            )

            context.user_data["messages_to_delete"] += [message]

            return AddRoomDialogStates.FLAT_HEIGHT

    message = await update.effective_message.reply_text(
        text='Площадь квартиры (пропустить -> /0)',
    )

    await update_message_and_delete_messages(update, context, data)

    context.user_data["messages_to_delete"] += [message]

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

    await update_message_and_delete_messages(update, context, data)

    context.user_data["messages_to_delete"] += [message]

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

    await update.effective_message.reply_text(
        text='Дом является памятником?',
        reply_markup=get_house_is_historical_keyboard(0),
    )

    await update_message_and_delete_messages(update, context, data)

    return AddRoomDialogStates.HOUSE_IS_HISTORICAL


async def change_house_is_historical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        house_is_historical = bool(int(call_back_data.split('_')[-1]))
        data.house_is_historical = house_is_historical
        context.user_data[effective_message_id] = data

    await update.effective_message.reply_text(
        text='Есть лифт рядом в квартирой?',
        reply_markup=get_yes_or_no_keyboard(callback_pattern='is_elevator_nearby_'),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
    )

    return AddRoomDialogStates.ELEVATOR_NEARBY


async def change_elevator_nearby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        elevator_nearby = bool(int(call_back_data.split('_')[-1]))

        data.elevator_nearby = elevator_nearby
        context.user_data[effective_message_id] = data

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
    )

    if data.flour == 2:
        await update.effective_message.reply_text(
            text='Помещение под этой квартирой жилое?',
            reply_markup=get_yes_or_no_keyboard(callback_pattern='room_under_is_living_'),
        )

        return AddRoomDialogStates.ROOM_UNDER
    else:
        data.room_under_is_living = True
        context.user_data[effective_message_id] = data
        await update.effective_message.reply_text(
            text='Тип подъезда',
            reply_markup=get_entrance_type_keyboard(advertisement_id=0),
        )

        return AddRoomDialogStates.ENTRANCE_TYPE


async def change_room_under(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        room_under_is_living = bool(int(call_back_data.split('_')[-1]))

        data.room_under_is_living = room_under_is_living
        context.user_data[effective_message_id] = data

    await update.effective_message.reply_text(
        text='Вход в парадную откуда?',
        reply_markup=get_entrance_type_keyboard(advertisement_id=0),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
    )

    return AddRoomDialogStates.ENTRANCE_TYPE


async def change_entrance_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        entrance_type = EntranceType[call_back_data.split('_')[-1]]

        data.entrance_type = entrance_type
        context.user_data[effective_message_id] = data

    await update.effective_message.reply_text(
        text='Окна комнаты выходят куда?',
        reply_markup=get_view_type_keyboard(advertisement_id=0),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
    )

    return AddRoomDialogStates.WINDOWS_TYPE


async def change_view_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        windows_type = ViewType[call_back_data.split('_')[-1]]

        data.view_type = windows_type
        context.user_data[effective_message_id] = data

    await update.effective_message.reply_text(
        text='Санузел в квартире какой?',
        reply_markup=get_toilet_type_keyboard(advertisement_id=0),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
    )

    return AddRoomDialogStates.TOILET_TYPE


async def change_toilet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        toilet_type = ToiletType[call_back_data.split('_')[-1]]

        data.toilet_type = toilet_type
        context.user_data[effective_message_id] = data

    message = await update.effective_message.reply_text(
        text='Введите информацию о комнатах (пропустить. -> /0)\n'
             'Пример: <i>5/28.6-Ж(2пенс МиЖ НОТ), 8/33.0-Н(М ПП), 9/24.9-Н(М ПИС)</i>\n'
             'Комнаты обязательно должны быть разделены запятой.',
        reply_markup=None,
        parse_mode='HTML'
    )

    context.user_data["messages_to_delete"] += [message]

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
    )

    return AddRoomDialogStates.ROOMS_INFO


async def change_rooms_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    if update.message.text != '/0':
        # full_pattern = r"((\d+)/(\d+([.,]\d+)?)[\s-]?([ЖНСРжнср\s])\((.*)\))[.,]?"
        # search_pattern = r"(\d+)/(\d+([.,]\d+)?)[\s-]?([ЖНСРжнср\s])\(([^)]*)\)[.,]?"
        search_pattern = r"(\d+)\/(\d+([.,]\d*)?)(.[^,]*\))"
        rooms_info = update.message.text

        matches = re.findall(search_pattern, rooms_info)

        print(matches)

        if len(matches) != data.number_of_rooms_in_flat:
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
            )

            rooms.append(room)

        data.rooms_info = rooms
        context.user_data[effective_message_id] = data

    await update_message_and_delete_messages(update, context, data)

    keyboard = get_appropriate_keyboard(0, data)

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(data),
        reply_markup=keyboard,
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

    text = get_appropriate_text(data)
    if advertisement.added_by:
        text += DISPATCHER_USERNAME_TEMPLATE.format(
            username=advertisement.added_by.username,
            date=advertisement.added_at.strftime('%d.%m'),
        )

    admins = await user_service.get_admins(session)
    for admin in admins:
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
    return ConversationHandler.END


async def cancel_plan_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления план (данные не сохранены)',
    )
    await delete_messages(context)
    return ConversationHandler.END


async def cancel_phone_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления телефона (данные не сохранены)',
    )
    await delete_messages(context)
    return ConversationHandler.END


async def cancel_info_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_messages(context)
    await update.effective_message.reply_text(
        'Отмена добавления информации (данные не сохранены)',
    )
    return ConversationHandler.END


async def send_advertisement(session, bot: Bot, advertisement_id: int, user_id: int):
    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
    await session.refresh(advertisement, attribute_names=["room"])
    await session.refresh(advertisement.room, attribute_names=["rooms_info"])
    advertisement = AdvertisementResponse.model_validate(advertisement)

    data = DataToGather(
        **advertisement.model_dump(),
        **advertisement.room.model_dump(),
    )

    text = get_appropriate_text(data)
    if advertisement.added_by:
        text += DISPATCHER_USERNAME_TEMPLATE.format(
            username=advertisement.added_by.username,
            date=advertisement.added_at.strftime('%d.%m'),
        )

    await bot.send_photo(
        chat_id=user_id,
        photo=data.plan_telegram_file_id,
        reply_markup=get_plan_inspection_keyboard(advertisement_id=advertisement.advertisement_id),
        caption=text,
        parse_mode='HTML',
    )


async def view_advertisement(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        await session.commit()

        if status == AdvertisementStatus.VIEWED:
            await update.callback_query.answer(
                'Объявление помечено как хорошее',
                show_alert=True,
            )

            advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
            dispatcher = await user_service.get_user(session, advertisement.added_by_id)
            await send_advertisement(session, context.bot, advertisement_id, dispatcher.id)
        elif status == AdvertisementStatus.CANCELED:
            await update.callback_query.answer(
                'Объявление помечено как плохое',
                show_alert=True,
            )
    # await update.effective_message.edit_reply_markup(reply_markup=None)
    await delete_messages(context)
    await update.effective_message.delete()


async def show_data_from_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get(update.effective_message.id)

    if not data:
        await update.callback_query.answer(
            text='К сожалению данные для этого сообщения потерялись',
            show_alert=True,
        )

    await update.callback_query.answer()

    await update.effective_message.reply_text(
        text=fill_data_from_advertisement_template(data),
        reply_markup=get_delete_keyboard(advertisement_id=0),
    )


async def delete_message_data_from_advertisement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    await update.effective_message.delete()


async def start_calculate_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    ad_id = int(data.split('_')[-1])
    context.user_data[update.effective_message.id] = {'ad_id': ad_id}

    message = await update.effective_message.reply_text(
        'Цена 1м2 квартиры на продажу, тыс.руб',
    )

    context.user_data["messages_to_delete"] = [message]
    context.user_data['effective_message_id'] = update.effective_message.id

    return CalculateRoomDialogStates.PRICE_PER_METER_FOR_BUY


async def process_price_per_meter_for_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await validate_message_text(update, context, r'\d+([.,]\d+)?'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data['price_per_meter_for_buy'] = float(update.message.text.replace(',', '.'))

    message = await update.effective_message.reply_text(
        'Срок расселения, мес',
    )

    context.user_data["messages_to_delete"] += [message, update.message]

    return CalculateRoomDialogStates.LIVING_PERIOD


async def process_living_period(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await validate_message_text(update, context, r'\d+'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data['living_period'] = float(update.message.text.replace(',', '.'))

    message = await update.effective_message.reply_text(
        'Цена 1м2 продажи комнаты, тыс.руб',
    )

    context.user_data["messages_to_delete"] += [message, update.message]

    return CalculateRoomDialogStates.PRICE_PER_METER_FOR_SELL


async def process_price_per_meter_for_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await validate_message_text(update, context, r'\d+([.,]\d+)?'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data['price_per_meter_for_sell'] = float(update.message.text.replace(',', '.'))

    message = await update.effective_message.reply_text(
        'Процент комиссии агентства, %',
    )

    context.user_data["messages_to_delete"] += [message, update.message]

    return CalculateRoomDialogStates.AGENT_COMMISSION


async def process_agent_commission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await validate_message_text(update, context, r'\d+([.,]\d+)?'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data['agent_commission'] = float(update.message.text.replace(',', '.'))

    await update.message.delete()
    await delete_messages(context)

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]

    try:
        session = context.session
    except AttributeError:
        raise Exception('Session is not in context')

    advertisement = await advertisement_service.get_advertisement(session, data.get('ad_id'))

    await session.refresh(advertisement, attribute_names=['room'])
    await session.refresh(advertisement.room, attribute_names=["rooms_info"])
    await session.refresh(advertisement, attribute_names=['added_by'])

    advertisement = AdvertisementResponse.model_validate(advertisement)

    # Цена кв-ры и комиссия АН: (165*112,6)=>18579*0,1=1858
    # Маржа ЖкОП минус комиссия на 1м2 (МБК на1м2): (112.6-86.5)=>26.1*165=>4306-1858=>2448/86,5=>28
    # Цена доли: 165*33,0=5445 / Доходность инвестора % годовых (срок 6 мес): (28/165)*100*2=>34

    price_per_meter_for_buy = data.get('price_per_meter_for_buy')
    agent_commission = data.get('agent_commission')
    living_period = data.get('living_period')
    price_per_meter_for_sell = data.get('price_per_meter_for_sell')
    # living_period = 6
    # price_per_meter_for_sell = 160

    if not price_per_meter_for_buy or not agent_commission or not living_period or not price_per_meter_for_sell:
        await update.callback_query.answer(
            'Заполните все поля',
            show_alert=True,
        )
        return

    total_living_area = sum([room.area for room in advertisement.room.rooms_info])
    non_living_area = advertisement.room.flat_area - total_living_area

    flat_price = round(price_per_meter_for_buy * advertisement.room.flat_area)
    agent_commission_price = round(flat_price * agent_commission / 100)

    non_living_price = non_living_area * price_per_meter_for_buy
    something = non_living_price - agent_commission_price
    something_per_meter = something / total_living_area

    rooms_info_text = ''
    room_info_template = '{room_number}/{room_area}-{status}={refusal} -> Д={part_price}'
    room_for_sale_addition = ' -- КОМ({price_per_meter_for_sell})={room_price} -- {living_period}мес={profit_year_percent}%'

    for el in advertisement.room.rooms_info:
        part_price = round(
            price_per_meter_for_buy * advertisement.room.flat_area * el.area / total_living_area * (1 - agent_commission / 100),
        )
        rooms_info_text += room_info_template.format(
            room_number=el.number,
            room_area=el.area,
            # description=el.description,
            status='',
            refusal='',
            part_price=part_price
        )
        if 'ПП' in el.description:
            rooms_info_text += room_for_sale_addition.format(
                price_per_meter_for_sell=int(price_per_meter_for_sell),
                living_period=int(living_period),
                profit_year_percent=round(
                    (part_price - price_per_meter_for_sell * el.area) / (price_per_meter_for_sell * el.area) * 100 * (12 / living_period),
                ),
                room_price=round(el.area * price_per_meter_for_sell)
            )
        rooms_info_text += '\n'

    text = CALCULATING_RESULT_TEMPLATE.format(
        address=advertisement.room.address,
        flat_number=advertisement.room.flat_number,
        cadastral_number=advertisement.room.cadastral_number,
        is_historical='Памятник' if advertisement.room.house_is_historical else '',
        flour=advertisement.room.flour,
        room_under='(кв)' if advertisement.room.under_room_is_living else '(н)',
        flours_in_building=advertisement.room.flours_in_building,
        elevator='бл' if not advertisement.room.elevator_nearby else '',
        entrance_type=advertisement.room.entrance_type,
        windows_type=advertisement.room.view_type,
        toilet_type=advertisement.room.toilet_type,
        flat_area=advertisement.room.flat_area,
        living_area=round(total_living_area, 2),
        living_area_percent=int(total_living_area / advertisement.room.flat_area * 100),
        flat_height=advertisement.room.flat_height,
        price=advertisement.price // 1000,
        price_per_meter=int(advertisement.price / advertisement.room.room_area / 1000),
        rooms_info=rooms_info_text,
        price_per_meter_for_buy=int(price_per_meter_for_buy),
        flat_price=flat_price,
        agent_commission=int(agent_commission),
        agent_commission_price=agent_commission_price,
        mbk=round(something_per_meter),
    )

    await update.effective_message.reply_text(
        text=text,
        reply_markup=get_calculate_keyboard(advertisement_id=advertisement.advertisement_id),
    )

    return ConversationHandler.END


async def calculate_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    await update.effective_message.delete()


async def cancel_calculating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.effective_message.reply_text(
        'Отмена расчета (данные не сохранены)',
    )
    await delete_messages(context)
    await update.message.delete()
    await asyncio.sleep(5)
    await message.delete()
    return ConversationHandler.END


