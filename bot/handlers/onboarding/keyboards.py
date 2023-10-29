from telegram import KeyboardButton, ReplyKeyboardMarkup
from .static_text import (
    ADD_ROOM_KEYBOARD_TEXT,
    STATISTICS_KEYBOARD_TEXT,
    CANCEL_KEYBOARD_TEXT,
    SET_ROLE_KEYBOARD_TEXT,
    GET_ROLES_KEYBOARD_TEXT,
)


def get_dispatcher_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(STATISTICS_KEYBOARD_TEXT),
            KeyboardButton(ADD_ROOM_KEYBOARD_TEXT),
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(STATISTICS_KEYBOARD_TEXT),
            KeyboardButton(ADD_ROOM_KEYBOARD_TEXT),
        ],
        [
            KeyboardButton(SET_ROLE_KEYBOARD_TEXT),
            KeyboardButton(GET_ROLES_KEYBOARD_TEXT),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(CANCEL_KEYBOARD_TEXT)
        ]
    ]
    return ReplyKeyboardMarkup(keyboard)
