from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.utils.utils import validate_message_text, delete_messages, delete_message_or_skip
from bot.utils.resend_old_message import check_and_resend_old_message

from bot.crud import advertisement as advertisement_service
from database.enums import RoomRefusalStatusEnum

from .manage_data import CalculateRoomDialogStates
from .static_text import CALCULATING_RESULT_TEMPLATE
from .keyboards import get_calculate_keyboard


async def start_calculate_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_message = await check_and_resend_old_message(update, context)

    await update.callback_query.answer()
    data = update.callback_query.data
    ad_id = int(data.split('_')[-1])
    context.user_data[effective_message.id] = {'ad_id': ad_id}

    message = await update.effective_message.reply_text(
        'Цена 1м2 квартиры на продажу, тыс.руб',
    )

    context.user_data["messages_to_delete"] = [message]
    context.user_data['effective_message_id'] = effective_message.id

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

    advertisement_orm = await advertisement_service.get_advertisement(session, data.get('ad_id'))
    advertisement_orm = await advertisement_service.refresh_advertisement(session, advertisement_orm)
    advertisement = advertisement_service.convert_advertisement_to_advertisement_base(advertisement_orm)

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

    total_living_area = sum([room.area for room in advertisement.flat.rooms])
    non_living_area = advertisement.flat.area - total_living_area

    flat_price = round(price_per_meter_for_buy * advertisement.flat.area)
    agent_commission_price = round(flat_price * agent_commission / 100)

    non_living_price = non_living_area * price_per_meter_for_buy
    something = non_living_price - agent_commission_price
    something_per_meter = something / total_living_area

    rooms_info_text = ''
    room_info_template = '{room_number}/{room_area}-{status}={refusal} -> Д={part_price}'
    room_for_sale_addition = ' -- КОМ({price_per_meter_for_sell})={room_price} -- {living_period}мес={profit_year_percent}%'

    for room in advertisement.flat.rooms:
        part_price = round(
            price_per_meter_for_buy * advertisement.flat.area * room.area / total_living_area * (
                        1 - agent_commission / 100),
        )
        rooms_info_text += room_info_template.format(
            room_number=room.number_on_plan,
            room_area=room.area,
            description=room.comment,
            status=room.status.value,
            refusal=room.refusal_status.value if room.refusal_status else '',
            part_price=part_price
        )
        if room.refusal_status in [RoomRefusalStatusEnum.ROOM_ON_CROSS_SALE, RoomRefusalStatusEnum.ROOM_ON_DIRECT_SALE]:
            rooms_info_text += room_for_sale_addition.format(
                price_per_meter_for_sell=int(price_per_meter_for_sell),
                living_period=int(living_period),
                profit_year_percent=round(
                    (part_price - price_per_meter_for_sell * room.area) / (price_per_meter_for_sell * room.area) * 100 * (
                                12 / living_period),
                ),
                room_price=round(room.area * price_per_meter_for_sell)
            )
        rooms_info_text += '\n'

    text = CALCULATING_RESULT_TEMPLATE.format(
        address=advertisement.flat.house.street_name + ' ' + advertisement.flat.house.number,
        flat_number=advertisement.flat.flat_number,
        cadastral_number=advertisement.flat.cadastral_number,
        is_historical='Памятник' if advertisement.flat.house.is_historical else '',
        flour=advertisement.flat.flour,
        room_under='(кв)' if advertisement.flat.under_room_is_living else '(н)',
        flours_in_building=advertisement.flat.house.number_of_flours,
        elevator='бл' if not advertisement.flat.elevator_nearby else '',
        entrance_type=advertisement.flat.house_entrance_type.value,
        windows_type=' '.join([el.value for el in advertisement.flat.view_type]),
        toilet_type=advertisement.flat.toilet_type.value,
        flat_area=advertisement.flat.area,
        living_area=round(total_living_area, 2),
        living_area_percent=int(total_living_area / advertisement.flat.area * 100),
        flat_height=advertisement.flat.flat_height,
        price=advertisement.room_price // 1000,
        price_per_meter=int(advertisement.room_price / advertisement.room_area / 1000),
        rooms_info=rooms_info_text,
        price_per_meter_for_buy=int(price_per_meter_for_buy),
        flat_price=flat_price,
        agent_commission=int(agent_commission),
        agent_commission_price=agent_commission_price,
        mbk=round(something_per_meter),
    )

    await update.effective_message.reply_text(
        text=text,
        reply_markup=get_calculate_keyboard(advertisement_id=advertisement.id),
    )

    return ConversationHandler.END


async def calculate_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    await update.effective_message.delete()


async def cancel_calculating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_messages(context)
    await delete_message_or_skip(update.effective_message)
    return ConversationHandler.END
