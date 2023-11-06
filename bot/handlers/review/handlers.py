from telegram import Update, Bot
from telegram.ext import ContextTypes

from bot.service import advertisement as advertisement_service
from bot.service import user as user_service

from bot.utils.utils import delete_messages

from bot.handlers.rooms.handlers import get_appropriate_text

from database.types import DataToGather, AdvertisementResponse
from database.enums import AdvertisementStatus


from .keyboards import get_plan_inspection_keyboard


async def send_advertisement(session, bot: Bot, advertisement_id: int, user_id: int):
    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
    await session.refresh(advertisement, attribute_names=["room"])
    await session.refresh(advertisement.room, attribute_names=["rooms_info"])
    await session.refresh(advertisement, attribute_names=["added_by"])
    advertisement = AdvertisementResponse.model_validate(advertisement)

    data = DataToGather(
        **advertisement.model_dump(),
        **advertisement.room.model_dump(),
    )

    text = get_appropriate_text(data)

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
                'Отправлено диспетчеру',
                show_alert=True,
            )

            advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
            dispatcher = await user_service.get_user(session, advertisement.added_by_id)
            await send_advertisement(session, context.bot, advertisement_id, dispatcher.id)
        elif status == AdvertisementStatus.CANCELED:
            await update.callback_query.answer(
                'Объявление помечено как отмененное',
                show_alert=True,
            )

    await delete_messages(context)
    await update.effective_message.delete()