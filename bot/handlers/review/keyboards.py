from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.utils import structure_buttons
from bot.handlers.rooms.manage_data import fill_user_fio_template
from database.models import User

active_emoji = '📝'
filled_emoji = '✅'


def get_plan_inspection_keyboard(
        advertisement_id: int,
        plan_is_filled: bool = False,
        plan_is_active: bool = False,
        phone_is_filled: bool = False,
        phone_is_active: bool = False,
        info_is_filled: bool = False,
        info_is_active: bool = False,
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                (active_emoji if plan_is_active else filled_emoji if plan_is_filled else '') +
                'План',
                callback_data=f'change_plan_{advertisement_id}',
            ),
            InlineKeyboardButton(
                (active_emoji if phone_is_active else filled_emoji if phone_is_filled else '') +
                'Телефон',
                callback_data=f'change_phone_{advertisement_id}',
            ),
            InlineKeyboardButton(
                (active_emoji if info_is_active else filled_emoji if info_is_filled else '') +
                'Инфо',
                callback_data=f'change_info_{advertisement_id}',
            ),
        ],
        [
            InlineKeyboardButton(
                'Осмотр',
                callback_data=f'start_plan_inspection_{advertisement_id}',
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_users_keyboard(callback_prefix: str, users: list[User]) -> InlineKeyboardMarkup:
    keyboard = []
    for user in users:
        fio = fill_user_fio_template(user)
        keyboard.append(
            InlineKeyboardButton(
                fio,
                callback_data=f'{callback_prefix}_{user.id}',
            )
        )
    keyboard = structure_buttons(keyboard, 2)
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                'Да',
                callback_data=f'confirm_user_attachment_{advertisement_id}_1',
            ),
            InlineKeyboardButton(
                'Нет',
                callback_data=f'confirm_user_attachment_{advertisement_id}_0',
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
