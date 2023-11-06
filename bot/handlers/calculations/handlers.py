from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.utils.utils import validate_message_text, delete_messages

from bot.service import advertisement as advertisement_service

from database.types import AdvertisementResponse

from .manage_data import CalculateRoomDialogStates
from .static_text import CALCULATING_RESULT_TEMPLATE
from .keyboards import get_calculate_keyboard

import asyncio


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
        'Комиссия АН, %',
    )

    context.user_data["messages_to_delete"] += [message, update.message]

    return CalculateRoomDialogStates.AGENT_COMMISSION


async def process_agent_commission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await validate_message_text(update, context, r'\d+([.,]\d+)?'):
        return

    effective_message_id = context.user_data['effective_message_id']
    data = context.user_data[effective_message_id]
    data['agent_commission'] = float(update.message.text.replace(',', '.'))

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
    context.user_data[effective_message_id]['price_per_meter_for_sell'] = float(
        update.message.text.replace(',', '.')
    )

    await update.message.delete()
    await delete_messages(context)

    await process_calculation(update, context)

    return ConversationHandler.END


async def process_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            price_per_meter_for_buy * advertisement.room.flat_area * el.area / total_living_area * (
                        1 - agent_commission / 100),
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
                    (part_price - price_per_meter_for_sell * el.area) / (price_per_meter_for_sell * el.area) * 100 * (
                                12 / living_period),
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
