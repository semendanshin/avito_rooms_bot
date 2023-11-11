from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Room, RoomInfo
from database.types import RoomInfoResponse, RoomInfoCreate
from typing import Optional, Sequence
import asyncio


loop = asyncio.get_event_loop()


async def create_rooms_info(session: AsyncSession, rooms_info: list[RoomInfoCreate], main_room: Room) -> list[RoomInfo]:
    rooms_info = [RoomInfo(**room_info.model_dump(), main_room=main_room) for room_info in rooms_info]
    session.add_all(rooms_info)
    return rooms_info


async def create_room_info(session: AsyncSession, room_info: RoomInfoCreate) -> RoomInfo:
    room_info = RoomInfo(**room_info.model_dump())
    session.add(room_info)
    return room_info


async def get_room_info(session: AsyncSession, room_info_id: int) -> Optional[RoomInfo]:
    result = await session.execute(select(RoomInfo).filter(RoomInfo.id == room_info_id))
    room_info = result.scalars().first()
    if not room_info:
        return None
    return room_info


async def get_room_info_by_room_id(session: AsyncSession, room_id: int) -> Sequence[RoomInfo]:
    result = await session.execute(select(RoomInfo).filter(RoomInfo.main_room_id == room_id))
    room_info = result.scalars().all()
    if not room_info:
        return None
    return room_info


async def update_room_info(session: AsyncSession, room_id: int, new_rooms_info: list[RoomInfoCreate]) -> list[RoomInfo]:
    room_info = await get_room_info_by_room_id(session, room_id)
    if not room_info:
        raise ValueError('Room info not found')
    new = [RoomInfo(**room_info.model_dump(), main_room_id=room_id) for room_info in new_rooms_info]
    for el in new:
        session.add(el)
    for el in room_info:
        await session.delete(el)
    await session.commit()
    return new
