from database.models import Flat
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.schemas.types import FlatCreate


async def get_flat(session: AsyncSession, cadastral_number: str) -> Flat:
    flat = await session.execute(
        select(Flat).filter_by(cadastral_number=cadastral_number)
    )
    flat = flat.scalars().first()
    return flat


async def create_flat(session: AsyncSession, flat: FlatCreate) -> Flat:
    if await get_flat(session, flat.cadastral_number):
        raise ValueError('This flat already exists')

    flat = Flat(**flat.model_dump())
    session.add(flat)
    return flat
