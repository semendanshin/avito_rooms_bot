from sqlalchemy.ext.asyncio import AsyncSession

from database.enums import RoomTypeEnum
from database.models import Room

from bot.crud import advertisement as advertisement_service
from bot.schemas.types import RoomBase

from .static_text import ROOMS_INFO_TEXT, ROOM_TEMPLATE
from .schemas import RoomInfoBase, RoomsInfoBase


async def get_room_info_base_from_advertisement_id(session: AsyncSession, advertisement_id: int) -> RoomsInfoBase:
    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
    advertisement = await advertisement_service.refresh_advertisement(session, advertisement)
    rooms_info_base = RoomsInfoBase(rooms=[])
    for room in advertisement.flat.rooms:
        rooms_info_base.rooms.append(RoomInfoBase(
            room_number=room.number_on_plan,
            room_area=room.area,
            room_type=room.type,
            room_occupants={occupant: room.occupants.count(occupant) for occupant in set(room.occupants)},
            room_owners={owner: room.owners.count(owner) for owner in set(room.owners)},
            room_status=room.status,
            room_refusal_status=room.refusal_status,
            comment=room.comment,
        ))
    return rooms_info_base


def fill_rooms_info_base_template(rooms_info_base: RoomsInfoBase) -> str:
    result = ROOMS_INFO_TEXT
    for room in rooms_info_base.rooms:
        result += fill_room_info_base_template(room) + '\n'
    return result


def fill_room_info_base_template(room_info_base: RoomInfoBase) -> str:
    return ROOM_TEMPLATE.format(
        number=room_info_base.room_number,
        area=room_info_base.room_area,
        type=room_info_base.room_type.value if room_info_base.room_type else '',
        owners=' '.join([f'{count}{owner.value}' for owner, count in room_info_base.room_owners.items()]),
        occupants=' '.join([f'{count}{occupant.value}' for occupant, count in room_info_base.room_occupants.items()]),
        status=room_info_base.room_status.value if room_info_base.room_status else '',
        refusal_status=room_info_base.room_refusal_status.value if room_info_base.room_refusal_status else '',
        comment=room_info_base.comment if room_info_base.comment else '',
    )


def check_rooms_info_base_filled(rooms_info_base: RoomsInfoBase) -> bool:
    return all(
        [
            check_room_info_base_filled(room)
            for room in filter(lambda room: room.room_type == RoomTypeEnum.LIVING, rooms_info_base.rooms)
        ]
    ) and rooms_info_base.rooms != []


def check_room_info_base_filled(room_info_base: RoomInfoBase) -> bool:
    return (
            room_info_base.room_number is not None and
            room_info_base.room_area is not None and
            room_info_base.room_type is not None and
            (any(room_info_base.room_occupants[key] for key in room_info_base.room_occupants.keys())
             if room_info_base.room_status == RoomTypeEnum.LIVING else True) and
            any(room_info_base.room_owners[key] for key in room_info_base.room_owners.keys()) and
            room_info_base.room_status is not None and
            room_info_base.room_refusal_status is not None
    )


def convert_rooms_info_base_to_rooms_base(rooms_info: list[RoomInfoBase]) -> list[RoomBase]:
    rooms = []
    for room_info in rooms_info:
        rooms.append(
            RoomBase(
                number_on_plan=str(room_info.room_number),
                area=room_info.room_area,
                type=room_info.room_type,
                occupants=[occupant for occupant, count in room_info.room_occupants.items() for _ in range(count)],
                owners=[owner for owner, count in room_info.room_owners.items() for _ in range(count)],
                status=room_info.room_status,
                refusal_status=room_info.room_refusal_status,
                comment=room_info.comment,
            )
        )
    return rooms


def convert_rooms_base_to_rooms_info_base(rooms: list[RoomBase]) -> RoomsInfoBase:
    rooms_info_base = RoomsInfoBase(rooms=[])
    for room in rooms:
        rooms_info_base.rooms.append(RoomInfoBase(
            room_number=room.number_on_plan,
            room_area=room.area,
            room_type=room.type,
            room_occupants={occupant: room.occupants.count(occupant) for occupant in set(room.occupants)},
            room_owners={owner: room.owners.count(owner) for owner in set(room.owners)},
            room_status=room.status,
            room_refusal_status=room.refusal_status,
            comment=room.comment,
        ))
    return rooms_info_base


async def update_rooms_in_advertisement(session: AsyncSession, advertisement_id: int, rooms: list[RoomBase]):
    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
    advertisement = await advertisement_service.refresh_advertisement(session, advertisement)

    for room in advertisement.flat.rooms:
        await session.delete(room)

    for room in rooms:
        session.add(
            Room(**room.model_dump(), flat_cadastral_number=advertisement.flat.cadastral_number)
        )

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e

    advertisement = await advertisement_service.refresh_advertisement(session, advertisement)

    return advertisement
