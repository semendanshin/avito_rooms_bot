from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from database.enums import UserRole


def get_roles_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=UserRole.AGENT.value,
                    callback_data=f'set_role_{UserRole.AGENT.value}',
                ),
                InlineKeyboardButton(
                    text=UserRole.DISPATCHER.value,
                    callback_data=f'set_role_{UserRole.DISPATCHER.value}',
                ),
            ],
            [
                InlineKeyboardButton(
                    text=UserRole.USER.value,
                    callback_data=f'set_role_{UserRole.USER.value}',
                ),
            ]
        ],
    )
