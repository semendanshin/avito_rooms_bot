from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Room, RoomInfo
from database.types import RoomInfoResponse, RoomInfoCreate
from typing import Optional
import asyncio


loop = asyncio.get_event_loop()


async def create_rooms_info(session: AsyncSession, rooms_info: list[RoomInfoCreate], main_room: Room) -> list[RoomInfo]:
    rooms_info = [RoomInfo(**room_info.model_dump(), main_room=main_room) for room_info in rooms_info]
    session.add_all(rooms_info)
    await session.commit()
    await session.refresh(main_room)
    return rooms_info


async def create_room_info(session: AsyncSession, room_info: RoomInfoCreate) -> RoomInfo:
    room_info = RoomInfo(**room_info.model_dump())
    session.add(room_info)
    await session.commit()
    await session.refresh(room_info)
    return RoomInfoResponse.model_validate(room_info)


async def get_room_info(session: AsyncSession, room_info_id: int) -> Optional[RoomInfo]:
    result = await session.execute(select(RoomInfo).filter(RoomInfo.id == room_info_id))
    room_info = result.scalars().first()
    if not room_info:
        return None
    return room_info
