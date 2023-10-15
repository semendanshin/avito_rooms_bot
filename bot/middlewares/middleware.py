from telegram import Update
from telegram.ext import ContextTypes
from .abstract_middleware import AbstractMiddleware


class Middleware:
    def __init__(self, middlewares: list[AbstractMiddleware]):
        self.middlewares = middlewares

    async def on_update(self, update: Update, context: ContextTypes):
        for middleware in self.middlewares:
            await middleware.on_update(update, context)

    async def after_update(self, update: Update, context: ContextTypes):
        for middleware in self.middlewares:
            await middleware.after_update(update, context)
