from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Inspection


async def get_inspection_by_id(session: AsyncSession, inspection_id: int) -> Inspection:
    inspection = await session.execute(
        select(Inspection).filter_by(id=inspection_id)
    )
    inspection = inspection.scalars().first()
    return inspection


async def get_inspection_by_advertisement_id(session: AsyncSession, advertisement_id: int) -> Inspection:
    inspection = await session.execute(
        select(Inspection).filter_by(advertisement_id=advertisement_id)
    )
    inspection = inspection.scalars().first()
    return inspection
