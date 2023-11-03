from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from .manage_data import InspectionTimePeriods


def get_time_periods_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                '18:30 - 19:30',
                callback_data=f'set_time_{InspectionTimePeriods.p1.name}',
            ),
            InlineKeyboardButton(
                '19:00 - 20:00',
                callback_data=f'set_time_{InspectionTimePeriods.p2.name}',
            ),
        ],
        [
            InlineKeyboardButton(
                '19:30 - 20:30',
                callback_data=f'set_time_{InspectionTimePeriods.p3.name}',
            ),
            InlineKeyboardButton(
                '20:00 - 21:00',
                callback_data=f'set_time_{InspectionTimePeriods.p4.name}',
            ),
        ],
        [
            InlineKeyboardButton(
                '12:00 - 14:00',
                callback_data=f'set_time_{InspectionTimePeriods.p5.name}',
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                'Отменить',
                callback_data='cancel_plan_inspection',
            ),
            InlineKeyboardButton(
                'Подтвердить',
                callback_data='confirm_plan_inspection',
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
