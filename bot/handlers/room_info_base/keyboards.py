from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.utils.keyboards import get_enum_options_keyboard, structure_buttons

from database.enums import RoomTypeEnum, RoomOccupantsEnum, RoomOwnersEnum, RoomStatusEnum, RoomRefusalStatusEnum

from .schemas import RoomInfoBase, RoomsInfoBase

from typing import Optional, Type
from enum import Enum as PyEnum

ADD_ROOM_CALLBACK_DATA = 'rooms_info_add_room'
EDIT_ROOM_CALLBACK_DATA = 'rooms_info_edit_room'
SAVE_CALLBACK_DATA = 'rooms_info_save'

ADD_ROOM_TEXT = 'Добавить'
EDIT_ROOM_TEXT = 'Изм'
SAVE_TEXT = 'ОК'


def get_rooms_info_base_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(EDIT_ROOM_TEXT, callback_data=EDIT_ROOM_CALLBACK_DATA),
                InlineKeyboardButton(ADD_ROOM_TEXT, callback_data=ADD_ROOM_CALLBACK_DATA),
            ],
            [
                InlineKeyboardButton(SAVE_TEXT, callback_data=SAVE_CALLBACK_DATA),
            ],
        ]
    )


ROOM_TYPE_CALLBACK_DATA = 'rooms_info_room_type'


def get_room_type_keyboard() -> InlineKeyboardMarkup:
    return get_enum_options_keyboard(RoomTypeEnum, ROOM_TYPE_CALLBACK_DATA)


def get_keyboard_from_dict_of_enums(enum: Type[PyEnum], dictionary: dict[Type[PyEnum], int], callback_prefix: str)\
        -> InlineKeyboardMarkup:
    keyboard = []
    for enum_option in enum:
        if enum_option in dictionary and dictionary[enum_option]:
            text = f'{dictionary[enum_option]} {enum_option.value}'
        else:
            text = enum_option.value

        keyboard.append(
            InlineKeyboardButton(
                text,
                callback_data=f'{callback_prefix}_{enum_option.name}'
            )
        )
    keyboard = structure_buttons(keyboard, 3)
    keyboard.extend(
        [
            [
                InlineKeyboardButton('Готово', callback_data=f'{callback_prefix}_done'),
            ],
            # [
            #     InlineKeyboardButton('Пропустить', callback_data=f'{callback_prefix}_skip'),
            # ]
        ]
    )
    return InlineKeyboardMarkup(keyboard)


ROOM_OCCUPANTS_CALLBACK_DATA = 'rooms_info_room_occupants'


def get_room_occupants_keyboard(occupants: Optional[dict[RoomOccupantsEnum, int]] = None) -> InlineKeyboardMarkup:
    if occupants is None:
        occupants = {}

    return get_keyboard_from_dict_of_enums(RoomOccupantsEnum, occupants, ROOM_OCCUPANTS_CALLBACK_DATA)


ROOM_OWNERS_CALLBACK_DATA = 'rooms_info_room_owners'


def get_room_owners_keyboard(owners: Optional[dict[RoomOwnersEnum, int]] = None) -> InlineKeyboardMarkup:
    if owners is None:
        owners = {}

    return get_keyboard_from_dict_of_enums(RoomOwnersEnum, owners, ROOM_OWNERS_CALLBACK_DATA)


ROOM_STATUS_CALLBACK_DATA = 'rooms_info_room_status'


def get_room_status_keyboard() -> InlineKeyboardMarkup:
    return get_enum_options_keyboard(RoomStatusEnum, ROOM_STATUS_CALLBACK_DATA)


ROOM_REFUSAL_STATUS_CALLBACK_DATA = 'rooms_info_room_refusal_status'


def get_room_refusal_status_keyboard() -> InlineKeyboardMarkup:
    return get_enum_options_keyboard(RoomRefusalStatusEnum, ROOM_REFUSAL_STATUS_CALLBACK_DATA)


PICK_ROOM_TO_EDIT_CALLBACK_DATA = 'rooms_info_pick_room_to_edit'


def get_show_rooms_to_edit_keyboard(rooms_info: list[RoomInfoBase]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            f'{room.room_number}/{room.room_area}',
            callback_data=f'{PICK_ROOM_TO_EDIT_CALLBACK_DATA}_{room.room_number}'
        )
        for room in rooms_info
    ]
    keyboard = structure_buttons(buttons, 2)
    keyboard.append(
        [
            InlineKeyboardButton('Назад', callback_data=f'{PICK_ROOM_TO_EDIT_CALLBACK_DATA}_back'),
        ]
    )
    return InlineKeyboardMarkup(keyboard)


EDIT_OR_DELETE_ROOM_CALLBACK_DATA = 'rooms_info_edit_or_delete_room'


def get_edit_od_delete_keyboard(room_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    'Удалить',
                    callback_data=f'{EDIT_OR_DELETE_ROOM_CALLBACK_DATA}_{room_number}_delete'
                ),
                InlineKeyboardButton(
                    'Изменить',
                    callback_data=f'{EDIT_OR_DELETE_ROOM_CALLBACK_DATA}_{room_number}_edit'
                ),
            ],
            [
                InlineKeyboardButton('Назад', callback_data=f'{EDIT_OR_DELETE_ROOM_CALLBACK_DATA}_back'),
            ]
        ]
    )
