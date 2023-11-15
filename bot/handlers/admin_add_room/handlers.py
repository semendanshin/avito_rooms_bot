import pprint

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, ExtBot

from bot.crud import advertisement as advertisement_service
from bot.crud import house as house_service
from bot.crud import user as user_service
from bot.crud import flat as flat_service

from bot.utils.dadata_repository import dadata
from bot.utils.utils import delete_message_or_skip, delete_messages

from bot.handlers.review.keyboards import get_users_keyboard
from bot.handlers.rooms.manage_data import get_advertisement_base
from bot.handlers.rooms.handlers import get_appropriate_text, get_appropriate_keyboard

from avito_parser import scrape_avito_room_ad, TooManyRequests, AvitoScrapingException

from .keyboards import get_confirm_keyboard
from .manage_data import AdminAddAdvertisementConversationSteps

import re


async def start_ad_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text(
        'Введите ссылку на объявление',
    )
    context.user_data['messages_to_delete'] = [update.message, message]
    return AdminAddAdvertisementConversationSteps.ADD_URL


async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if await advertisement_service.get_advertisement_by_url(context.session, url):
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

    dadata_data = dadata.get_clean_data(result.address + 'литера А')
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

    house = await house_service.get_house(context.session, dadata_data.house_cadnum)
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
    await delete_message_or_skip(update.effective_message)

    context.user_data['effective_advertisement'] = advertisement

    message = await update.message.reply_text(
        f'Адрес: {dadata_data.street_with_type}, {dadata_data.house}\n'
        f'Кадастровый номер: {dadata_data.house_cadnum}\n'
        'Все верно?',
        reply_markup=get_confirm_keyboard('confirm_address'),
    )

    context.user_data['messages_to_delete'].append(message)

    return AdminAddAdvertisementConversationSteps.CONFIRM_ADDRESS


async def confirm_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    data = update.callback_query.data.split('_')

    answer = int(data[-1])

    if answer:
        await delete_messages(context)

        message = await update.callback_query.message.reply_text(
            'Введите номер квартиры, если известно (пропустить -> /0',
        )
        context.user_data['messages_to_delete'].extend([message, update.callback_query.message])
        return AdminAddAdvertisementConversationSteps.ADD_FLAT_NUMBER
    else:
        await delete_messages(context)

        message = await update.message.reply_text(
            'Введите ссылку на объявление',
        )
        context.user_data['messages_to_delete'] = [update.message, message]
        return AdminAddAdvertisementConversationSteps.ADD_URL


async def add_flat_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    advertisement = context.user_data['effective_advertisement']

    if update.message.text != '/0':
        message = await update.effective_message.reply_text(
            text='Кадастровый номер (пропустить -> /0) <a href="https://dadata.ru/suggestions/#address">Дадата</a>',
            parse_mode='HTML',
            disable_web_page_preview=True,
        )

        context.user_data["messages_to_delete"] += [message, update.message]

        advertisement.flat.flat_number = update.message.text

        house_address = 'спб ' + advertisement.flat.house.street_name + ' ' + advertisement.flat.house.number
        address = dadata.get_clean_data(house_address + 'литера А, кв' + advertisement.flat.flat_number)
        if not address or not address.flat_cadnum:
            address = dadata.get_clean_data(house_address + ',кв. ' + advertisement.flat.flat_number)
            if not address or not address.flat_cadnum:
                address = None

        if address and address.flat_cadnum:
            message = await update.effective_message.reply_text(
                text=f'Кадастровый номер: {address.flat_cadnum}',
            )
            context.user_data["messages_to_delete"] += [message]

            if address.flat_cadnum and await flat_service.get_flat(context.session, address.flat_cadnum):
                message = await update.effective_message.reply_text(
                    text='Квартира с таким кадастровым номером уже существует. Отменяю добавление.',
                )
                context.user_data["messages_to_delete"] += [message]

                return ConversationHandler.END

            advertisement.flat.cadastral_number = address.flat_cadnum

            if address.flat_area:
                message = await update.effective_message.reply_text(
                    text=f'Площадь квартиры: {address.flat_area} м2',
                )
                context.user_data["messages_to_delete"] += [message]
                advertisement.flat.area = float(address.flat_area.replace(',', '.'))

    dispatchers = await user_service.get_dispatchers(context.session)

    if not dispatchers:
        await update.message.reply_text(
            'Нет диспетчеров. Отменяю добавление.',
        )

        await delete_messages(context)
        await delete_message_or_skip(update.effective_message)

        return ConversationHandler.END

    await update.message.reply_text(
        'Выберите диспетчера',
        reply_markup=get_users_keyboard('choose_dispatcher', dispatchers),
    )
    context.user_data['messages_to_delete'].extend([update.message])

    return AdminAddAdvertisementConversationSteps.CHOOSE_DISPATCHER


async def flat_already_exists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ...


async def choose_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split('_')

    dispatcher_id = int(data[-1])

    advertisement = context.user_data['effective_advertisement']

    text = get_appropriate_text(advertisement)
    keyboard = get_appropriate_keyboard(-1, advertisement)

    message = await context.bot.send_message(
        dispatcher_id,
        text=text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode='HTML',
    )

    application = context.application
    dispatcher_user_data = application.user_data[dispatcher_id]
    dispatcher_user_data[message.id] = advertisement

    context.bot_data[dispatcher_id] = message.id

    await update.callback_query.answer(
        'Отправлено диспетчеру',
        show_alert=True,
    )

    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)

    return ConversationHandler.END
