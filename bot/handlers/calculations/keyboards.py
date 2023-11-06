from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_calculate_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                'Удалить',
                callback_data=f'calculate_delete_{advertisement_id}',
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
