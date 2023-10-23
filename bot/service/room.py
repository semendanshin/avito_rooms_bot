from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Room
from database.types import RoomCreate
from typing import Optional


async def get_room(session: AsyncSession, room_id: int) -> Optional[Room]:
    result = await session.execute(select(Room).filter(Room.id == room_id))
    room = result.scalars().first()
    return room


async def create_room(session: AsyncSession, room: RoomCreate) -> Room:
    if await get_room(session, room.id):
        raise ValueError('This room already exists')

    room = Room(**room.model_dump())
    session.add(room)
    return room
