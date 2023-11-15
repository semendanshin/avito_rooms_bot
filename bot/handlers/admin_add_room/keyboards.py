from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_confirm_keyboard(callback_data_prefix: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                'Да',
                callback_data=callback_data_prefix + '_1'
            ),
            InlineKeyboardButton(
                'Нет',
                callback_data=callback_data_prefix + '_0'
            )
        ]
    ])

