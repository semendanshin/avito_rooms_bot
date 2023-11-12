import logging
from telegram import Update
from telegram.ext import ContextTypes
from .abstract_middleware import AbstractMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from bot.crud import user as user_service
from bot.schemas.types import UserCreate


class UserMiddleware(AbstractMiddleware):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def on_update(self, update: Update, context: ContextTypes):
        try:
            session: AsyncSession = context.__getattribute__('session')
        except AttributeError:
            raise Exception('SessionMiddleware: session is not found in context')
        else:
            user = await user_service.get_user(session, update.effective_user.id)
            if not user:
                user_create = UserCreate(
                    id=update.effective_user.id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name,
                    last_name=update.effective_user.last_name,
                )
                user = await user_service.create_user(session, user_create)
            context.__setattr__('database_user', user)

    async def after_update(self, update: Update, context: ContextTypes):
        try:
            context.__delattr__('database_user')
        except AttributeError:
            pass
