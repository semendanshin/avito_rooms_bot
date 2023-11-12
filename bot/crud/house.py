from database.models import House
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.schemas.types import HouseCreate


async def get_house(session: AsyncSession, cadastral_number: str) -> House:
    house = await session.execute(
        select(House).filter_by(cadastral_number=cadastral_number)
    )
    house = house.scalars().first()
    return house


async def create_house(session: AsyncSession, house: HouseCreate) -> House:
    if await get_house(session, house.cadastral_number):
        raise ValueError('This house already exists')

    house = House(**house.model_dump())
    session.add(house)
    return house

