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
from telegram import Update

from bot.middlewares import Middleware, SessionMiddleware, UserMiddleware

from bot.utils.error import send_stacktrace_to_tg_chat

from bot.handlers.onboarding import handlers as onboarding_handlers
from bot.handlers.rooms import handlers as rooms_handlers
from bot.handlers.role import handlers as role_handlers
from bot.handlers.inspection_planing import handlers as inspection_planing_handlers
from bot.handlers.calculations import handlers as calculations_handlers
from bot.handlers.review import handlers as review_handlers

from bot.handlers.onboarding.static_text import (
    ADD_ROOM_KEYBOARD_TEXT,
    STATISTICS_KEYBOARD_TEXT,
    CANCEL_KEYBOARD_TEXT,
    SET_ROLE_KEYBOARD_TEXT,
    GET_ROLES_KEYBOARD_TEXT,
)

from bot.handlers.calculations.manage_data import CalculateRoomDialogStates
from bot.handlers.review.manage_data import ReviewConversationStates
from bot.handlers.role.manage_data import AddRoleConversationSteps

from bot.config import config
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import logging
from logging.handlers import RotatingFileHandler


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
                # ('start', 'Запустить бота'),
                # ('add_room', 'Добавить квартиру'),
                # ('set_role', 'Дать роль'),
                # ('get_roles', 'Посмотреть пользователей с ролью'),
                # ('cancel', 'Отменить')
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
                CommandHandler('0', rooms_handlers.change_cadastral_number),
                MessageHandler(
                    filters=filters.TEXT & ~filters.Command(),
                    callback=rooms_handlers.change_cadastral_number,
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
                CallbackQueryHandler(
                    rooms_handlers.change_house_is_historical,
                    pattern=r'is_historical_.*',
                )
            ],
            rooms_handlers.AddRoomDialogStates.ELEVATOR_NEARBY: [
                CallbackQueryHandler(
                    rooms_handlers.change_elevator_nearby,
                    pattern=r'is_elevator_nearby_.*',
                )
            ],
            rooms_handlers.AddRoomDialogStates.ROOM_UNDER: [
                CallbackQueryHandler(
                    rooms_handlers.change_room_under,
                    pattern=r'room_under_is_living_.*',
                )
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
            entry_points=[
                CommandHandler('set_role', role_handlers.start_give_role),
                MessageHandler(
                    filters=filters.Text(SET_ROLE_KEYBOARD_TEXT),
                    callback=role_handlers.start_give_role,
                )
            ],
            states={
                AddRoleConversationSteps.GET_USERNAME: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=role_handlers.save_username,
                    ),
                ],
                AddRoleConversationSteps.GET_ROLE: [
                    CallbackQueryHandler(role_handlers.save_role, pattern=r'set_role_.*'),
                ],
                AddRoleConversationSteps.CONFIRM_ROLE: [
                    CallbackQueryHandler(role_handlers.confirm_role, pattern=r'confirm_role_.*'),
                ],
                AddRoleConversationSteps.GET_FIO: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=role_handlers.save_fio,
                    ),
                ],
                AddRoleConversationSteps.GET_PHONE: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=role_handlers.save_phone,
                    ),
                ],
            },
            fallbacks=[CommandHandler('cancel', role_handlers.cancel_role_adding)],
            persistent=True,
            name='set_role_handler',
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    review_handlers.view_advertisement,
                    pattern=r'review_.*',
                )
            ],
            states={
                ReviewConversationStates.CHOOSE_DISPATCHER: [
                    CallbackQueryHandler(
                        review_handlers.attach_dispatcher,
                        pattern=r'attach_dispatcher_.*',
                    ),
                ],
                ReviewConversationStates.CHOOSE_AGENT: [
                    CallbackQueryHandler(
                        review_handlers.attach_agent,
                        pattern=r'attach_agent_.*',
                    ),
                ],
                ReviewConversationStates.CONFIRMATION: [
                    CallbackQueryHandler(
                        review_handlers.confirm_attachment,
                        pattern=r'confirm_user_attachment_.*',
                    ),
                ],
            },
            fallbacks=[CommandHandler('cancel', review_handlers.cancel_attachment)],
            name='review_handler',
            persistent=True,
        )
    )

    app.add_handler(CallbackQueryHandler(
        rooms_handlers.delete_message_data_from_advertisement,
        pattern=r'delete_parsed_.*',
    ))

    app.add_handler(
        CommandHandler(
            'get_roles',
            role_handlers.get_users_with_role,
        )
    )

    app.add_handler(
        MessageHandler(
            filters=filters.Text(GET_ROLES_KEYBOARD_TEXT),
            callback=role_handlers.get_users_with_role,
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[CallbackQueryHandler(
                calculations_handlers.start_calculate_room,
                pattern=r'calculate_start.*',
            )],
            states={
                CalculateRoomDialogStates.PRICE_PER_METER_FOR_BUY: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=calculations_handlers.process_price_per_meter_for_buy,
                    ),
                ],
                CalculateRoomDialogStates.AGENT_COMMISSION: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=calculations_handlers.process_agent_commission,
                    ),
                ],
                CalculateRoomDialogStates.LIVING_PERIOD: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=calculations_handlers.process_living_period,
                    ),
                ],
                CalculateRoomDialogStates.PRICE_PER_METER_FOR_SELL: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=calculations_handlers.process_price_per_meter_for_sell,
                    ),
                ],
            },
            fallbacks=[CommandHandler('cancel', calculations_handlers.cancel_calculating)],
            name='calculate_room_handler',
            persistent=True,
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    inspection_planing_handlers.start_inspection_planing,
                    pattern=r'start_plan_inspection_.*',
                ),
            ],
            states={
                inspection_planing_handlers.InspectionPlaningConversationSteps.GET_DATE: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=inspection_planing_handlers.save_date,
                    ),
                ],
                inspection_planing_handlers.InspectionPlaningConversationSteps.GET_TIME: [
                    CallbackQueryHandler(
                        inspection_planing_handlers.save_time,
                        pattern=r'set_time_.*',
                    ),
                ],
                inspection_planing_handlers.InspectionPlaningConversationSteps.GET_CONTACT_INFO: [
                    MessageHandler(
                        filters=filters.TEXT & ~filters.Command(),
                        callback=inspection_planing_handlers.save_contact,
                    ),
                ],
                inspection_planing_handlers.InspectionPlaningConversationSteps.GET_METING_TIP: [
                    MessageHandler(
                        filters=(filters.TEXT | filters.PHOTO) & ~filters.Command(),
                        callback=inspection_planing_handlers.save_meting_tip,
                    ),
                ],
                inspection_planing_handlers.InspectionPlaningConversationSteps.CONFIRM: [
                    CallbackQueryHandler(
                        inspection_planing_handlers.confirm,
                        pattern=r'confirm_plan_.*'
                    ),
                    CallbackQueryHandler(
                        inspection_planing_handlers.cancel,
                        pattern=r'cancel_plan_.*'
                    )
                ]
            },
            fallbacks=[CommandHandler('cancel', inspection_planing_handlers.cancel_inspection_planing)],
            name='plan_inspection_handler',
            persistent=True,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            calculations_handlers.calculate_delete,
            pattern=r'calculate_delete_.*',
        )
    )

    app.add_handler(TypeHandler(Update, middleware.after_update), group=1)

    app.add_error_handler(send_stacktrace_to_tg_chat)

    app.run_polling()


if __name__ == '__main__':
    main()
