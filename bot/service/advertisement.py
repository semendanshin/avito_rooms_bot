from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Advertisement
from database.types import AdvertisementCreate
from database.types import AdvertisementStatus
from typing import Optional


async def create_advertisement(session: AsyncSession, advertisement: AdvertisementCreate) -> Advertisement:
    advertisement = Advertisement(**advertisement.model_dump())
    session.add(advertisement)
    await session.commit()
    await session.refresh(advertisement)
    await session.refresh(advertisement, attribute_names=["added_by", "viewed_by", "assigned_to", "room"])
    return advertisement


async def get_advertisement(session: AsyncSession, advertisement_id: int) -> Optional[Advertisement]:
    result = await session.execute(select(Advertisement).filter(Advertisement.id == advertisement_id))
    advertisement = result.scalars().first()
    if not advertisement:
        return None
    await session.refresh(advertisement, attribute_names=["added_by", "viewed_by", "assigned_to", "room"])
    return advertisement


async def get_advertisement_by_url(session: AsyncSession, url: str) -> Optional[Advertisement]:
    result = await session.execute(select(Advertisement).filter(Advertisement.url == url))
    advertisement = result.scalars().first()
    if not advertisement:
        return None
    await session.refresh(advertisement, attribute_names=["added_by", "viewed_by", "assigned_to", "room"])
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
    await session.commit()
    await session.refresh(advertisement)
    await session.refresh(advertisement, attribute_names=["added_by", "viewed_by", "assigned_to", "room"])
    return advertisement
