from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    TypeHandler,
    PicklePersistence,
    PersistenceInput,
    filters,
)
from telegram import Update, BotCommand

from bot.middlewares import Middleware, SessionMiddleware, UserMiddleware

from bot.handlers.onboarding import handlers as onboarding_handlers
from bot.handlers.onboarding.static_text import ADD_ROOM_KEYBOARD_TEXT, STATISTICS_KEYBOARD_TEXT
from bot.handlers.rooms import handlers as rooms_handlers
from bot.handlers.role import handlers as role_handlers
from bot.config import config
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import logging
from logging.handlers import RotatingFileHandler
import asyncio


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        RotatingFileHandler("logs/bot.log", maxBytes=200000, backupCount=5),
        logging.StreamHandler(),
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands(
            [
                ('start', 'Запустить бота'),
                ('add_room', 'Добавить квартиру'),
                ('set_role', 'Дать роль'),
                ('get_roles', 'Посмотреть пользователей с ролью'),
                ('cancel', 'Отменить')
            ]
        )

    engine = create_async_engine(config.db_url.get_secret_value(), echo=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    middleware = Middleware(
        [
            SessionMiddleware(session_maker),
            UserMiddleware(),
        ],
    )

    TOKEN = config.bot_token.get_secret_value()

    persistence_input = PersistenceInput(bot_data=True, user_data=True, chat_data=False, callback_data=False)
    persistence = PicklePersistence('bot/persistence.pickle', store_data=persistence_input, update_interval=1)
    app = Application.builder().token(TOKEN).persistence(persistence).post_init(post_init).build()

    app.add_handler(TypeHandler(Update, middleware.on_update), group=-1)

    app.add_handler(CommandHandler('start', onboarding_handlers.start))

    plan_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(rooms_handlers.start_change_plan, pattern=r'change_plan_.*')],
        states={
            rooms_handlers.AddRoomDialogStates.FLAT_PLAN: [
                MessageHandler(
                    filters=filters.PHOTO,
                    callback=rooms_handlers.change_plan,
                ),
            ],
        },
        fallbacks=[CommandHandler('cancel', rooms_handlers.cancel_plan_adding)],
        persistent=True,
        name='plan_handler',
    )

    phone_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(rooms_handlers.start_change_phone, pattern=r'change_phone_.*')],
        states={
            rooms_handlers.AddRoomDialogStates.CONTACT_PHONE: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_phone,
                ),
            ],
        },
        fallbacks=[CommandHandler('cancel', rooms_handlers.cancel_phone_adding)],
        persistent=True,
        name='phone_handler',
    )

    info_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(rooms_handlers.start_change_info, pattern=r'change_info_.*')],
        states={
            rooms_handlers.AddRoomDialogStates.FLAT_NUMBER: [
                CommandHandler('0', rooms_handlers.change_flat_number),
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_flat_number,
                ),
            ],
            rooms_handlers.AddRoomDialogStates.KADASTR_NUMBER: [
                CommandHandler('0', rooms_handlers.change_kadastr_number),
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_kadastr_number,
                ),
            ],
            rooms_handlers.AddRoomDialogStates.FLAT_HEIGHT: [
                CommandHandler('0', rooms_handlers.change_flat_height),
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_flat_height,
                ),
            ],
            rooms_handlers.AddRoomDialogStates.FLAT_AREA: [
                CommandHandler('0', rooms_handlers.change_flat_area),
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_flat_area,
                ),
            ],
            rooms_handlers.AddRoomDialogStates.HOUSE_IS_HISTORICAL: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_house_is_historical,
                ),
            ],
            rooms_handlers.AddRoomDialogStates.ELEVATOR_NEARBY: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_elevator_nearby,
                ),
            ],
            rooms_handlers.AddRoomDialogStates.ROOM_UNDER: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_room_under,
                ),
            ],
            rooms_handlers.AddRoomDialogStates.ENTRANCE_TYPE: [
                CallbackQueryHandler(rooms_handlers.change_entrance_type, pattern=r'entrance_type_.*'),
            ],
            rooms_handlers.AddRoomDialogStates.WINDOWS_TYPE: [
                CallbackQueryHandler(rooms_handlers.change_view_type, pattern=r'view_type.*'),
            ],
            rooms_handlers.AddRoomDialogStates.TOILET_TYPE: [
                CallbackQueryHandler(rooms_handlers.change_toilet_type, pattern=r'toilet_type.*'),
            ],
            rooms_handlers.AddRoomDialogStates.ROOMS_INFO: [
                CommandHandler('0', rooms_handlers.change_rooms_info),
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_rooms_info,
                ),
            ],
        },
        fallbacks=[CommandHandler('cancel', rooms_handlers.cancel_info_adding)],
        persistent=True,
        name='info_handler',
    )

    add_room_handler = ConversationHandler(
        entry_points=[
            CommandHandler('add_room', rooms_handlers.start_adding_room),
            MessageHandler(
                filters=filters.Text(ADD_ROOM_KEYBOARD_TEXT),
                callback=rooms_handlers.start_adding_room
            )
        ],
        states={
            rooms_handlers.AddRoomDialogStates.ROOM_URL: [
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.add_room_url,
                ),
            ],
        },
        fallbacks=[CommandHandler('cancel', rooms_handlers.cancel_room_adding)],
        persistent=True,
        name='add_room_handler',
    )

    app.add_handlers(
        [
            add_room_handler,
            phone_handler,
            plan_handler,
            info_handler,
            CallbackQueryHandler(rooms_handlers.send, pattern=r'send_.*'),
            CallbackQueryHandler(rooms_handlers.show_data_from_ad, pattern=r'show_data_.*'),
        ]
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler('set_role', role_handlers.start_give_role)],
            states={
                role_handlers.AddRoleConversationSteps.GET_USERNAME: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=role_handlers.save_username,
                    ),
                ],
                role_handlers.AddRoleConversationSteps.GET_ROLE: [
                    CallbackQueryHandler(role_handlers.save_role, pattern=r'set_role_.*'),
                ],
            },
            fallbacks=[CommandHandler('cancel', role_handlers.cancel_role_adding)],
            persistent=True,
            name='set_role_handler',
        )
    )

    app.add_handler(CallbackQueryHandler(
        rooms_handlers.view_advertisement,
        pattern=r'review_.*',
    ))

    app.add_handler(
        CommandHandler(
            'get_roles',
            role_handlers.get_users_with_role,
        )
    )

    app.add_handler(TypeHandler(Update, middleware.after_update), group=1)

    app.post_init

    app.run_polling()


if __name__ == '__main__':
    # asyncio.run(main())
    main()
