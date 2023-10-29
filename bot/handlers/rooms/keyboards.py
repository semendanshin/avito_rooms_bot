from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from database.enums import (EntranceTypeHumanReadable, ToiletTypeHumanReadable, ViewTypeHumanReadable,
                            AdvertisementStatus)

active_emoji = '📝'
filled_emoji = '✅'


def get_ad_editing_keyboard(
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
                'Реклама',
                callback_data=f'show_data_{advertisement_id}',
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_send_or_edit_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                filled_emoji + 'План',
                callback_data=f'change_plan_{advertisement_id}',
            ),
            InlineKeyboardButton(
                filled_emoji+ 'Телефон',
                callback_data=f'change_phone_{advertisement_id}',
            ),
            InlineKeyboardButton(
                filled_emoji + 'Инфо',
                callback_data=f'change_info_{advertisement_id}',
            ),
        ],
        [
            InlineKeyboardButton('Готово', callback_data=f'send_{advertisement_id}'),
        ],
        [
            InlineKeyboardButton(
                'Реклама',
                callback_data=f'show_data_{advertisement_id}',
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def structure_buttons(buttons: list, row_width: int = 2) -> list:
    result = [buttons[i:i + row_width] for i in range(0, len(buttons), row_width)]
    return result


def get_entrance_type_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(entrance_type.value, callback_data=f'entrance_type_{advertisement_id}_{entrance_type.name}')
        for entrance_type in EntranceTypeHumanReadable
    ]
    keyboard = structure_buttons(buttons, 2)
    keyboard += [[InlineKeyboardButton('Пропустить', callback_data=f'entrance_type_{advertisement_id}_skip')]]

    return InlineKeyboardMarkup(keyboard)


def get_view_type_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(view_type.value, callback_data=f'view_type_{advertisement_id}_{view_type.name}')
        for view_type in ViewTypeHumanReadable
    ]
    keyboard = structure_buttons(buttons, 2)
    keyboard += [[InlineKeyboardButton('Пропустить', callback_data=f'view_type_{advertisement_id}_skip')]]

    return InlineKeyboardMarkup(keyboard)


def get_toilet_type_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(toilet_type.value, callback_data=f'toilet_type_{advertisement_id}_{toilet_type.name}')
        for toilet_type in ToiletTypeHumanReadable
    ]
    keyboard = structure_buttons(buttons, 2)
    keyboard += [[InlineKeyboardButton('Пропустить', callback_data=f'toilet_type_{advertisement_id}_skip')]]

    return InlineKeyboardMarkup(keyboard)


def get_review_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                'НЕТ',
                callback_data=f'review_{AdvertisementStatus.CANCELED.name}_{advertisement_id}'
            ),
            InlineKeyboardButton(
                'СМ',
                callback_data=f'review_{AdvertisementStatus.VIEWED.name}_{advertisement_id}'
            ),
        ],
        [
            InlineKeyboardButton(
                'Расчет',
                callback_data=f'calculate_start_{advertisement_id}'
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_yes_or_no_keyboard(callback_pattern: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton('Да', callback_data=callback_pattern + '1'),
            InlineKeyboardButton('Нет', callback_data=callback_pattern + '0'),
        ],
        [
            InlineKeyboardButton('Пропустить', callback_data=callback_pattern + 'skip'),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


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


def get_delete_keyboard(advertisement_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                'Удалить',
                callback_data=f'delete_parsed_{advertisement_id}',
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
