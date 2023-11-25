from telegram import Update, Message, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler

from avito_parser import scrape_avito_room_ad, TooManyRequests, AvitoScrapingException, ClosedAd

from bot.schemas.types import AdvertisementBase, RoomBase, HouseBase
from database.enums import HouseEntranceType, ViewType, ToiletType, RoomTypeEnum, RoomStatusEnum, RoomOwnersEnum, \
    RoomRefusalStatusEnum, RoomOccupantsEnum, FlatEntranceType

from bot.crud import advertisement as advertisement_service, user as user_service
from ...crud import house as house_service, flat as flat_service

from bot.utils.utils import (
    validate_message_text,
    delete_messages,
    delete_message_or_skip,
)
from bot.utils.resend_old_message import check_and_resend_old_message
from bot.utils.dadata_repository import dadata

from typing import Optional
from logging import getLogger
import re

from .manage_data import (
    AddRoomDialogStates,
    fill_data_from_advertisement_template,
    fill_first_room_template,
    fill_parsed_room_template,
    get_advertisement_base,
    create_advertisement,
)
from .keyboards import (
    get_ad_editing_keyboard,
    get_entrance_type_keyboard,
    get_view_type_keyboard,
    get_toilet_type_keyboard,
    get_review_keyboard,
    get_yes_or_no_keyboard,
    get_delete_keyboard,
    get_house_is_historical_keyboard,
    get_send_or_edit_keyboard,
)

logger = getLogger(__name__)


def what_is_filled(advertisement: AdvertisementBase) -> (bool, bool, bool):
    plan_is_filled = bool(advertisement.flat.plan_telegram_file_id)
    phone_is_filled = bool(advertisement.contact_phone)
    info_is_filled = all(
        [
            advertisement.flat.flat_number,
            advertisement.flat.cadastral_number,
            advertisement.flat.rooms,
            advertisement.flat.area,
            advertisement.flat.under_room_is_living is not None,
            advertisement.flat.flat_height,
            advertisement.flat.house.is_historical is not None,
            advertisement.flat.elevator_nearby is not None,
            advertisement.flat.house_entrance_type,
            advertisement.flat.view_type,
            advertisement.flat.toilet_type,
        ]
    )
    return plan_is_filled, phone_is_filled, info_is_filled


def get_appropriate_text(advertisement: AdvertisementBase) -> str:
    if any(
            [
                advertisement.flat.flat_number,
                advertisement.flat.cadastral_number,
                advertisement.flat.rooms,
                advertisement.flat.area,
                advertisement.flat.under_room_is_living is not None,
                advertisement.flat.flat_height,
                advertisement.flat.elevator_nearby is not None,
                advertisement.flat.house_entrance_type,
                advertisement.flat.view_type,
                advertisement.flat.toilet_type,
            ]
    ):
        return fill_first_room_template(advertisement)
    else:
        return fill_parsed_room_template(advertisement)


def get_appropriate_keyboard(advertisement_id: int, advertisement: AdvertisementBase) -> InlineKeyboardMarkup:
    plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(advertisement)
    if all([plan_is_filled, phone_is_filled, info_is_filled]):
        return get_send_or_edit_keyboard(advertisement_id)
    else:
        return get_ad_editing_keyboard(
            advertisement_id=advertisement_id,
            plan_is_filled=plan_is_filled,
            phone_is_filled=phone_is_filled,
            info_is_filled=info_is_filled,
        )


async def edit_caption_or_text(message: Message, new_text: str,
                               reply_markup: Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup] = None):
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


async def update_message_and_delete_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, advertisement: AdvertisementBase):
    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
    )
    await delete_message_or_skip(update.message)
    await delete_messages(context)


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
            'Авито блокирует подключения. Невозможно получить данные с сайте. Напишите /cancel, чтобы отменить добавление',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return
    except ClosedAd:
        message = await update.message.reply_text(
            'Объявление снято с публикации. Напишите /cancel, чтобы отменить добавление',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return
    except AvitoScrapingException:
        message = await update.message.reply_text(
            'Не удалось получить информацию по ссылке, попробуйте еще раз. Напишите /cancel, чтобы отменить добавление',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return
    except Exception as e:
        message = await update.message.reply_text(
            'Неизвестная ошибка. Напишите /cancel, чтобы отменить добавление',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        raise e

    dadata_data = dadata.get_clean_data(result.address + 'литера А, кв')
    if not dadata_data or not dadata_data.house_cadnum:
        dadata_data = dadata.get_clean_data(result.address)
        if not dadata_data or not dadata_data.house_cadnum:
            dadata_data = None

    if not dadata_data or not dadata_data.street or not dadata_data.house or not dadata_data.house_cadnum:
        message = await update.message.reply_text(
            'Не удалось получить кадномер дома. Напишите /cancel, чтобы отменить добавление',
        )
        context.user_data['messages_to_delete'].extend([message, update.message])
        return

    advertisement = get_advertisement_base()

    house = await house_service.get_house(session, dadata_data.house_cadnum)
    if not house:
        advertisement.flat.house.cadastral_number = dadata_data.house_cadnum
        advertisement.flat.house.street_name = dadata_data.street + ' ' + dadata_data.street_type
        advertisement.flat.house.number = dadata_data.house
        advertisement.flat.house.number_of_flours = result.flours_in_building
        advertisement.flat.house.is_historical = None
    else:
        advertisement.flat.house = house

    advertisement.url = url
    advertisement.room_price = result.price
    advertisement.room_area = result.room_area
    advertisement.description = result.description
    advertisement.flat.number_of_rooms = result.number_of_rooms_in_flat
    advertisement.flat.flour = result.flour

    await delete_messages(context)
    await delete_message_or_skip(update.message)

    message = await update.message.reply_text(
        text=get_appropriate_text(advertisement),
        parse_mode='HTML',
        reply_markup=get_ad_editing_keyboard(advertisement_id=-1),
        disable_web_page_preview=True,
    )

    context.user_data[message.id] = advertisement
    context.bot_data[update.effective_user.id] = message.id

    return ConversationHandler.END


async def start_change_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message = await check_and_resend_old_message(update, context)

    await update.callback_query.answer()

    message = await update.effective_message.reply_text(
        'Вставьте картинку с планом',
    )
    plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(context.user_data[effective_message.id])
    await effective_message.edit_reply_markup(
        reply_markup=get_ad_editing_keyboard(
            advertisement_id=-1,
            plan_is_active=True,
            phone_is_filled=phone_is_filled,
            info_is_filled=info_is_filled,
        ),
    )
    context.user_data.update({'message_to_delete': message})
    return AddRoomDialogStates.FLAT_PLAN


async def change_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]
    advertisement.flat.plan_telegram_file_id = photo.file_id

    await update.message.delete()
    await context.user_data['message_to_delete'].delete()
    await context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['effective_message_id'],
    )

    keyboard = get_appropriate_keyboard(advertisement_id=-1, advertisement=advertisement)

    message = await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=get_appropriate_text(advertisement),
        parse_mode='HTML',
        reply_markup=keyboard,
    )
    del context.user_data[effective_message_id]
    context.user_data[message.id] = advertisement
    context.bot_data[update.effective_user.id] = message.id
    return ConversationHandler.END


async def start_change_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message = await check_and_resend_old_message(update, context)

    await update.callback_query.answer()

    advertisement_id = int(update.callback_query.data.split('_')[-1])
    if advertisement_id == -1:
        message = await update.effective_message.reply_text(
            'Введите телефон продавца и его имя и статус\nПример: <i>8999999999 А-Петр</i>',
            parse_mode='HTML',
        )
        plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(context.user_data[effective_message.id])
        await effective_message.edit_reply_markup(
            reply_markup=get_ad_editing_keyboard(
                advertisement_id=-1,
                plan_is_filled=plan_is_filled,
                phone_is_active=True,
                info_is_filled=info_is_filled,
            ),
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

    effective_message_id: int = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]
    advertisement.contact_phone = phone_number
    advertisement.contact_name = contact_name
    advertisement.contact_status = status
    context.user_data[effective_message_id] = advertisement

    keyboard = get_appropriate_keyboard(advertisement_id=-1, advertisement=advertisement)

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
        keyboard,
    )
    await update.message.delete()
    for message in context.user_data.get("messages_to_delete", []):
        await message.delete()
    context.user_data["messages_to_delete"] = []
    context.bot_data[update.effective_user.id] = effective_message_id
    return ConversationHandler.END


async def start_change_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message = await check_and_resend_old_message(update, context)

    await update.callback_query.answer()

    plan_is_filled, phone_is_filled, info_is_filled = what_is_filled(context.user_data[effective_message.id])
    await effective_message.edit_reply_markup(
        reply_markup=get_ad_editing_keyboard(
            advertisement_id=-1,
            plan_is_filled=plan_is_filled,
            phone_is_filled=phone_is_filled,
            info_is_active=True,
        ),
    )
    message = await update.effective_message.reply_text(
        'Номер квартиры (пропустить -> /0)',
    )
    context.user_data["messages_to_delete"] = [message]
    return AddRoomDialogStates.FLAT_NUMBER


async def change_flat_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if update.message.text == '/0':
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0) <a href="https://dadata.ru/suggestions/#address">Дадата</a>',
            parse_mode='HTML',
            disable_web_page_preview=True,
        )

        await update_message_and_delete_messages(update, context, advertisement)

        context.user_data["messages_to_delete"] += [message, update.message]

        return AddRoomDialogStates.KADASTR_NUMBER

    if not await validate_message_text(update, context, r'\d+([а-яА-Я]*)'):
        return

    advertisement.flat.flat_number = update.message.text

    await update_message_and_delete_messages(update, context, advertisement)

    house_address = 'спб ' + advertisement.flat.house.street_name + ' ' + advertisement.flat.house.number
    address = dadata.get_clean_data(house_address + 'литера А, кв' + advertisement.flat.flat_number)
    if not address or not address.flat_cadnum:
        address = dadata.get_clean_data(house_address + ',кв. ' + advertisement.flat.flat_number)
        if not address or not address.flat_cadnum:
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

    if address.flat_cadnum and await flat_service.get_flat(context.session, address.flat_cadnum):
        message = await update.effective_message.reply_text(
            text='Квартира с таким кадастровым номером уже существует. '
                 'Проверьте номер или напишите /cancel, чтобы отменить добавление',
        )
        context.user_data["messages_to_delete"] += [message]

        return AddRoomDialogStates.FLAT_NUMBER

    advertisement.flat.cadastral_number = address.flat_cadnum
    context.user_data[effective_message_id] = advertisement

    if address.flat_area:
        message = await update.effective_message.reply_text(
            text=f'Площадь квартиры: {address.flat_area} м2',
        )
        context.user_data["messages_to_delete"] += [message]
        advertisement.flat.area = float(address.flat_area.replace(',', '.'))
        context.user_data[effective_message_id] = advertisement

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
    advertisement = context.user_data[effective_message_id]

    if update.message.text != '/0':
        if not await validate_message_text(update, context, r'[\d:]*'):
            return

        if await flat_service.get_flat(context.session, update.message.text):
            message = await update.effective_message.reply_text(
                text='Квартира с таким кадастровым номером уже существует. '
                     'Проверьте номер или напишите /cancel, чтобы отменить добавление',
            )
            context.user_data["messages_to_delete"] += [message, update.message]

            return AddRoomDialogStates.KADASTR_NUMBER

        advertisement.flat.cadastral_number = update.message.text
        context.user_data[effective_message_id] = advertisement

        address = dadata.get_clean_data_by_cadastral_number(update.message.text)

        print(address.flat_area, address.flat_cadnum)
        print(address.flat_area, address.flat_cadnum)

        if address and address.flat_area:
            message = await update.effective_message.reply_text(
                text=f'Площадь квартиры: {address.flat_area} м2',
            )
            context.user_data["messages_to_delete"] += [message]
            advertisement.flat.area = float(address.flat_area.replace(',', '.'))
            context.user_data[effective_message_id] = advertisement

            message = await update.effective_message.reply_text(
                text='Высота потолка (пропустить -> /0)',
            )

            context.user_data["messages_to_delete"] += [message]

            return AddRoomDialogStates.FLAT_HEIGHT

    message = await update.effective_message.reply_text(
        text='Площадь квартиры (пропустить -> /0)',
    )

    await update_message_and_delete_messages(update, context, advertisement)

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.FLAT_AREA


async def change_flat_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if update.message.text != '/0':
        pattern = r'\d+([.,]\d+)?'

        if not await validate_message_text(update, context, pattern):
            return

        area = float(update.message.text.replace(',', '.'))

        advertisement.flat.area = area
        context.user_data[effective_message_id] = advertisement

    message = await update.effective_message.reply_text(
        text='Высота потолка (пропустить -> /0)',
    )

    await update_message_and_delete_messages(update, context, advertisement)

    context.user_data["messages_to_delete"] += [message]

    return AddRoomDialogStates.FLAT_HEIGHT


async def change_flat_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if update.message.text != '/0':
        if not await validate_message_text(update, context, r'\d+([.,]\d+)?'):
            return

        height = float(update.message.text.replace(',', '.'))

        advertisement.flat.flat_height = height
        context.user_data[effective_message_id] = advertisement

    await update.effective_message.reply_text(
        text='Дом является памятником?',
        reply_markup=get_house_is_historical_keyboard(-1),
    )

    await update_message_and_delete_messages(update, context, advertisement)

    return AddRoomDialogStates.HOUSE_IS_HISTORICAL


async def change_house_is_historical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        house_is_historical = bool(int(call_back_data.split('_')[-1]))
        advertisement.flat.house.is_historical = house_is_historical
        context.user_data[effective_message_id] = advertisement

    await update.effective_message.reply_text(
        text='Есть лифт рядом в квартирой?',
        reply_markup=get_yes_or_no_keyboard(callback_pattern='is_elevator_nearby_'),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
    )

    return AddRoomDialogStates.ELEVATOR_NEARBY


async def change_elevator_nearby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        elevator_nearby = bool(int(call_back_data.split('_')[-1]))

        advertisement.flat.elevator_nearby = elevator_nearby
        context.user_data[effective_message_id] = advertisement

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
    )

    if advertisement.flat.flour == 2:
        await update.effective_message.reply_text(
            text='Помещение под этой квартирой жилое?',
            reply_markup=get_yes_or_no_keyboard(callback_pattern='room_under_is_living_'),
        )

        return AddRoomDialogStates.ROOM_UNDER
    else:
        advertisement.flat.under_room_is_living = True
        context.user_data[effective_message_id] = advertisement
        await update.effective_message.reply_text(
            text='Вход в парадную откуда?',
            reply_markup=get_entrance_type_keyboard(advertisement_id=-1),
        )

        return AddRoomDialogStates.ENTRANCE_TYPE


async def change_room_under(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        room_under_is_living = bool(int(call_back_data.split('_')[-1]))

        advertisement.flat.under_room_is_living = room_under_is_living
        context.user_data[effective_message_id] = advertisement

    await update.effective_message.reply_text(
        text='Вход в парадную откуда?',
        reply_markup=get_entrance_type_keyboard(advertisement_id=-1),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
    )

    return AddRoomDialogStates.ENTRANCE_TYPE


async def change_entrance_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        house_entrance_type = HouseEntranceType[call_back_data.split('_')[-1]]

        advertisement.flat.house_entrance_type = house_entrance_type
        context.user_data[effective_message_id] = advertisement

    await update.effective_message.reply_text(
        text='Окна комнаты выходят куда?',
        reply_markup=get_view_type_keyboard(advertisement_id=-1),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
    )

    return AddRoomDialogStates.WINDOWS_TYPE


async def change_view_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        windows_type = ViewType[call_back_data.split('_')[-1]]

        advertisement.flat.view_type = [windows_type]
        advertisement.flat.windows_count = 1
        context.user_data[effective_message_id] = advertisement

    await update.effective_message.reply_text(
        text='Санузел в квартире какой?',
        reply_markup=get_toilet_type_keyboard(advertisement_id=-1),
    )

    await update.effective_message.delete()

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
    )

    return AddRoomDialogStates.TOILET_TYPE


async def change_toilet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    call_back_data = update.callback_query.data

    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if call_back_data.split('_')[-1] != 'skip':
        toilet_type = ToiletType[call_back_data.split('_')[-1]]

        advertisement.flat.toilet_type = toilet_type
        context.user_data[effective_message_id] = advertisement

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
        get_appropriate_text(advertisement),
    )

    return AddRoomDialogStates.ROOMS_INFO


async def change_rooms_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message_id = context.user_data['effective_message_id']
    advertisement = context.user_data[effective_message_id]

    if update.message.text != '/0':
        # full_pattern = r"((\d+)/(\d+([.,]\d+)?)[\s-]?([ЖНСРжнср\s])\((.*)\))[.,]?"
        # search_pattern = r"(\d+)/(\d+([.,]\d+)?)[\s-]?([ЖНСРжнср\s])\(([^)]*)\)[.,]?"
        search_pattern = r"(\d+)\/(\d+([.,]\d*)?)(.[^,]*\))"
        rooms_info = update.message.text

        matches = re.findall(search_pattern, rooms_info)

        print(matches)

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

            room = RoomBase(
                area=room_area,
                number_on_plan=room_plan_number,
                type=room_type,
                status=room_status,
                owners=room_owners,
                refusal_status=room_refusal_status,
                occupants=room_occupants,
                comment=room_comment,
            )

            rooms.append(room)

        advertisement.flat.rooms = rooms
        context.user_data[effective_message_id] = advertisement

    await update_message_and_delete_messages(update, context, advertisement)

    keyboard = get_appropriate_keyboard(-1, advertisement)

    await edit_caption_or_text(
        context.user_data['effective_message'],
        get_appropriate_text(advertisement),
        reply_markup=keyboard,
    )

    del context.user_data['effective_message_id']

    context.bot_data[update.effective_user.id] = context.user_data['effective_message']

    return ConversationHandler.END


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advertisement = context.user_data[update.effective_message.id]

    # tmp fix
    advertisement.flat.flat_entrance_type = FlatEntranceType.ONE
    advertisement.added_by = context.database_user
    for el in advertisement.flat.rooms:
        el.comment = ''

    advertisement = await create_advertisement(context.session, advertisement)

    text = get_appropriate_text(advertisement)

    admins = await user_service.get_admins(context.session)
    for admin in admins:
        message = await context.bot.send_photo(
            chat_id=admin.id,
            photo=advertisement.flat.plan_telegram_file_id,
            caption=text,
            reply_markup=get_review_keyboard(advertisement_id=advertisement.id),
            parse_mode='HTML',
        )
        context.bot_data[admin.id] = message.id

    await update.effective_message.delete()
    await update.callback_query.answer(
        text='Объявление добавлено',
        show_alert=True,
    )

    del context.user_data[update.effective_message.id]

    return ConversationHandler.END


async def cancel_room_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления комнаты (данные не сохранены)',
    )
    await delete_messages(context)
    await delete_message_or_skip(update.message)
    return ConversationHandler.END


async def cancel_plan_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления план (данные не сохранены)',
    )
    await delete_messages(context)
    await delete_message_or_skip(update.message)
    return ConversationHandler.END


async def cancel_phone_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Отмена добавления телефона (данные не сохранены)',
    )
    await delete_messages(context)
    await delete_message_or_skip(update.message)
    return ConversationHandler.END


async def cancel_info_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_messages(context)
    await delete_message_or_skip(update.message)
    await update.effective_message.reply_text(
        'Отмена добавления информации (данные не сохранены)',
    )
    return ConversationHandler.END


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
        reply_markup=get_delete_keyboard(advertisement_id=-1),
    )


async def delete_message_data_from_advertisement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await delete_message_or_skip(update.effective_message):
        await update.callback_query.answer(
            text='К сожалению не получается удалить это сообщение',
            show_alert=True,
        )
    else:
        await update.callback_query.answer()
