from telegram.ext import Application, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from .keyboards import (
    ADD_ROOM_CALLBACK_DATA,
    SAVE_CALLBACK_DATA,
    EDIT_ROOM_CALLBACK_DATA,
    ROOM_TYPE_CALLBACK_DATA,
    ROOM_OCCUPANTS_CALLBACK_DATA,
    ROOM_OWNERS_CALLBACK_DATA,
    ROOM_STATUS_CALLBACK_DATA,
    ROOM_REFUSAL_STATUS_CALLBACK_DATA,
    PICK_ROOM_TO_EDIT_CALLBACK_DATA,
    EDIT_OR_DELETE_ROOM_CALLBACK_DATA,
)
from .enums import RoomInfoBaseConversationSteps
from bot.handlers.room_info_base import handlers


def setup(application: Application):
    base_rooms_info_conversation_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                handlers.start,
                'change_rooms_*',
            ),
        ],
        states={
            RoomInfoBaseConversationSteps.SHOW_ROOMS_TO_EDIT: [
                CallbackQueryHandler(
                    handlers.stat_add_room,
                    ADD_ROOM_CALLBACK_DATA,
                ),
                CallbackQueryHandler(
                    handlers.show_rooms_to_edit,
                    EDIT_ROOM_CALLBACK_DATA,
                ),
                CallbackQueryHandler(
                    handlers.save,
                    SAVE_CALLBACK_DATA,
                ),
            ],
            RoomInfoBaseConversationSteps.ADD_ROOM_NUMBER: [
                MessageHandler(
                    filters.Text() & ~filters.Command(),
                    handlers.add_room_number,
                ),
            ],
            RoomInfoBaseConversationSteps.ADD_ROOM_AREA: [
                MessageHandler(
                    filters.Text() & ~filters.Command(),
                    handlers.add_room_area,
                ),
                CommandHandler(
                    '0',
                    handlers.add_room_area,
                ),
            ],
            RoomInfoBaseConversationSteps.ADD_ROOM_TYPE: [
                CallbackQueryHandler(
                    handlers.add_room_type,
                    ROOM_TYPE_CALLBACK_DATA,
                ),
            ],
            RoomInfoBaseConversationSteps.ADD_ROOM_OCCUPANTS: [
                CallbackQueryHandler(
                    handlers.add_room_occupants,
                    ROOM_OCCUPANTS_CALLBACK_DATA,
                ),
            ],
            RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS: [
                CallbackQueryHandler(
                    handlers.add_room_owners,
                    ROOM_OWNERS_CALLBACK_DATA,
                ),
            ],
            RoomInfoBaseConversationSteps.ADD_ROOM_STATUS: [
                CallbackQueryHandler(
                    handlers.add_room_status,
                    ROOM_STATUS_CALLBACK_DATA,
                ),
            ],
            RoomInfoBaseConversationSteps.ADD_ROOM_REFUSAL_STATUS: [
                CallbackQueryHandler(
                    handlers.add_room_refusal_status,
                    ROOM_REFUSAL_STATUS_CALLBACK_DATA,
                ),
            ],
            RoomInfoBaseConversationSteps.PICK_ROOM_TO_DELETE_OR_EDIT: [
                CallbackQueryHandler(
                    handlers.pick_room_to_edit_or_delete,
                    PICK_ROOM_TO_EDIT_CALLBACK_DATA,
                ),
            ],
            RoomInfoBaseConversationSteps.CHOOSE_DELETE_OR_EDIT: [
                CallbackQueryHandler(
                    handlers.delete_room_or_start_edit,
                    EDIT_OR_DELETE_ROOM_CALLBACK_DATA,
                ),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(
                handlers.save,
                SAVE_CALLBACK_DATA,
            ),
            CommandHandler(
                'cancel',
                handlers.cancel,
            ),
        ],
        persistent=True,
        name='rooms_info_base_conversation',
    )
    application.add_handler(base_rooms_info_conversation_handler)
