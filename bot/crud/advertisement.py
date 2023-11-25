from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Advertisement
from bot.schemas.types import AdvertisementCreate, AdvertisementResponse
from bot.schemas.types import AdvertisementStatus
from typing import Optional


async def create_advertisement(session: AsyncSession, advertisement: AdvertisementCreate) -> Advertisement:
    advertisement = Advertisement(**advertisement.model_dump())
    session.add(advertisement)
    return advertisement


async def get_advertisement(session: AsyncSession, advertisement_id: int) -> Optional[Advertisement]:
    result = await session.execute(select(Advertisement).filter(Advertisement.id == advertisement_id))
    advertisement = result.scalars().first()
    if not advertisement:
        return None
    return advertisement


async def get_advertisement_by_url(session: AsyncSession, url: str) -> Optional[Advertisement]:
    result = await session.execute(select(Advertisement).filter(Advertisement.url == url))
    advertisement = result.scalars().first()
    if not advertisement:
        return None
    return advertisement


async def update_advertisement_status(
        session: AsyncSession,
        advertisement_id: int,
        new_status: AdvertisementStatus,
        changed_by_user_id: int
) -> Advertisement:
    advertisement = await get_advertisement(session, advertisement_id)
    if not advertisement:
        raise ValueError('Advertisement not found')
    advertisement.status = new_status
    advertisement.viewed_by_id = changed_by_user_id
    advertisement.viewed_at = func.now()
    return advertisement


async def attach_dispatcher(session: AsyncSession, advertisement_id: int, user_id: int):
    advertisement = await get_advertisement(session, advertisement_id)
    if not advertisement:
        raise ValueError('Advertisement not found')
    advertisement.pinned_dispatcher_id = user_id
    await session.commit()
    return advertisement


async def attach_agent(session: AsyncSession, advertisement_id: int, user_id: int):
    advertisement = await get_advertisement(session, advertisement_id)
    if not advertisement:
        raise ValueError('Advertisement not found')
    advertisement.pinned_agent_id = user_id
    await session.commit()
    return advertisement


async def update_advertisement(session: AsyncSession, advertisement_id: int, new_data: AdvertisementCreate):
    advertisement = await get_advertisement(session, advertisement_id)
    if not advertisement:
        raise ValueError('Advertisement not found')
    for field, value in new_data.model_dump().items():
        setattr(advertisement, field, value)
    await session.commit()
    return advertisement


async def refresh_advertisement(session: AsyncSession, advertisement: Advertisement) -> Advertisement:
    await session.refresh(advertisement, ['flat'])
    await session.refresh(advertisement, ['added_by'])
    await session.refresh(advertisement.flat, ['house'])
    await session.refresh(advertisement.flat, ['rooms'])
    await session.refresh(advertisement.flat.house, ['flats'])
    return advertisement


def convert_advertisement_to_advertisement_base(advertisement: Advertisement) -> AdvertisementResponse:
    return AdvertisementResponse.model_validate(advertisement)
