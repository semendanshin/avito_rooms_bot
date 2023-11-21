from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from enum import Enum as PyEnum
from typing import Type


def structure_buttons(buttons: list[InlineKeyboardButton], row_width: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i:i + row_width] for i in range(0, len(buttons), row_width)]


def get_enum_options_keyboard(enum: Type[PyEnum], callback_pattern_start: str, row_width: int = 2,
                              skip_button: bool = True, done_button: bool = False)\
        -> InlineKeyboardMarkup:
    """
    Example:
    enum = ViewTypeHumanReadable
    callback_pattern_start = 'view_type'
    row_width = 2
    skip_button = True
    done_button = False
    result:
    [
        [
            InlineKeyboardButton('Вид из окна', callback_data='view_type_VIEW_FROM_WINDOW'),
            InlineKeyboardButton('Вид на окна', callback_data='view_type_VIEW_ON_WINDOWS'),
        ],
        [
            InlineKeyboardButton('Пропустить', callback_data='view_type_skip'),
        ]
    ]

    :param enum:
    :param callback_pattern_start:
    :param row_width:
    :param skip_button:
    :param done_button:
    :return:
    """
    buttons = [
        InlineKeyboardButton(option.value, callback_data=f'{callback_pattern_start}_{option.name}')
        for option in enum
    ]
    keyboard = structure_buttons(buttons, row_width)
    if done_button:
        keyboard += [[InlineKeyboardButton('Готово', callback_data=f'{callback_pattern_start}_done')]]
    if skip_button:
        keyboard += [[InlineKeyboardButton('Пропустить', callback_data=f'{callback_pattern_start}_skip')]]

    return InlineKeyboardMarkup(keyboard)
