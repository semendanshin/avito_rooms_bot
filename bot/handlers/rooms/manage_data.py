from enum import Enum
from bot.crud import advertisement as advertisement_service, room as room_service
from ...crud import house as house_service, flat as flat_service
from bot.schemas.types import AdvertisementBase, RoomBase, FlatBase, HouseBase
from bot.schemas.types import AdvertisementCreate, RoomCreate, FlatCreate, HouseCreate
from database.models import Advertisement, User, House, Room
from .static_text import (FIRST_ROOM_TEMPLATE, DATA_FROM_ADVERTISEMENT_TEMPLATE, FIO_TEMPLATE,
                          DISPATCHER_USERNAME_TEMPLATE, PARSED_ROOM_TEMPLATE, CONTACT_INFO_TEMPLATE)

from sqlalchemy.ext.asyncio import AsyncSession


class AddRoomDialogStates(Enum):
    """States for the add room dialog."""
    ROOM_URL = 'room_url'
    ADDITIONAL_INFO = 'additional_info'
    FLAT_PLAN = 'flat_plan'
    CONTACT_PHONE = 'contact_phone'
    FLAT_NUMBER = 'flat_number'
    FLAT_HEIGHT = 'flat_height'
    KADASTR_NUMBER = 'kadastr_number'
    FLAT_AREA = 'flat_area'
    HOUSE_IS_HISTORICAL = 'house_is_historical'
    ELEVATOR_NEARBY = 'elevator_nearby'
    ROOM_UNDER = 'room_under'
    ENTRANCE_TYPE = 'entrance_type'
    WINDOWS_TYPE = 'windows_type'
    TOILET_TYPE = 'toilet_type'
    ROOMS_INFO = 'rooms_info'
    MANUAL_ADDING = 'manual_adding'


def fill_data_from_advertisement_template(advertisement: AdvertisementBase) -> str:
    text = DATA_FROM_ADVERTISEMENT_TEMPLATE.format(
        room_area=advertisement.room_area,
        number_of_rooms_in_flat=advertisement.flat.number_of_rooms,
        flour=advertisement.flat.flour,
        flours_in_building=advertisement.flat.house.number_of_flours,
        address=advertisement.flat.house.street_name + ' ' + advertisement.flat.house.number,
        price=advertisement.room_price // 1000,
        price_per_meter=int(advertisement.room_price / advertisement.room_area // 1000),
    )
    text += '\n' + advertisement.description
    return text


def fill_parsed_room_template(advertisement: AdvertisementBase) -> str:
    text = PARSED_ROOM_TEMPLATE.format(
        room_area=advertisement.room_area,
        number_of_rooms_in_flat=advertisement.flat.number_of_rooms,
        flour=advertisement.flat.flour,
        flours_in_building=advertisement.flat.house.number_of_flours,
        address=advertisement.flat.house.street_name + ' ' + advertisement.flat.house.number,
        price=advertisement.room_price // 1000,
    )

    if advertisement.contact_phone:
        text += '\n' + CONTACT_INFO_TEMPLATE.format(
            contact_phone=advertisement.contact_phone,
            contact_status=advertisement.contact_status,
            contact_name=advertisement.contact_name,
        )

    return text


def fill_user_fio_template(user: User) -> str:
    return FIO_TEMPLATE.format(
        first_name=user.system_first_name if user.system_first_name else '',
        last_name_letter=user.system_last_name[
            0] if user.system_last_name else '',
        sur_name_letter=user.system_sur_name[0] if user.system_sur_name else '',
    )


def fill_first_room_template(advertisement: AdvertisementBase) -> str:
    living_area = round(sum([room.area for room in advertisement.flat.rooms]), 1) if advertisement.flat.rooms else ''
    living_area_percent = int(living_area / advertisement.flat.area * 100) if advertisement.flat.area and living_area else ''

    price_per_meter = int(advertisement.room_price / advertisement.room_area) // 1000 if advertisement.flat.area else ''
    price = advertisement.room_price // 1000

    elevator = 'бл' if advertisement.flat.elevator_nearby is not None and not advertisement.flat.elevator_nearby else ''

    if advertisement.flat.flour and advertisement.flat.flour == 2 and advertisement.flat.under_room_is_living is not None:
        room_under = '(кв)' if advertisement.flat.under_room_is_living else '(н)'
    else:
        room_under = ''

    rooms_info = '\n'.join(
        [
            f'{room.number_on_plan}/{room.area}{room.comment if room.comment else ""}'
            for room in advertisement.flat.rooms
        ]
    ) if advertisement.flat.rooms else ''

    windows_type = ', '.join([el.value for el in advertisement.flat.view_type]) if advertisement.flat.view_type else ''
    is_historical = 'памятник' if advertisement.flat.house.is_historical else ''

    text = FIRST_ROOM_TEMPLATE.format(
        address=str(advertisement.flat.house.street_name) + ' ' + str(advertisement.flat.house.number),
        flat_number=advertisement.flat.flat_number if advertisement.flat.flat_number else '',
        cadastral_number=advertisement.flat.cadastral_number if advertisement.flat.cadastral_number else '',
        price=str(price),
        price_per_meter=str(price_per_meter),
        living_area=str(living_area),
        living_area_percent=str(living_area_percent),
        flour=str(advertisement.flat.flour),
        room_under=room_under,
        flours_in_building=advertisement.flat.house.number_of_flours if advertisement.flat.house.number_of_flours else '',
        elevator=elevator,
        entrance_type=advertisement.flat.house_entrance_type.value if advertisement.flat.house_entrance_type else '',
        windows_type=windows_type,
        toilet_type=advertisement.flat.toilet_type.value if advertisement.flat.toilet_type else '',
        flat_area=advertisement.flat.area if advertisement.flat.area else '',
        room_area=advertisement.flat.flat_height if advertisement.flat.flat_height else '',
        flat_height=advertisement.flat.flat_height if advertisement.flat.flat_height else '',
        rooms_info=rooms_info,
        contact_phone=advertisement.contact_phone if advertisement.contact_phone else '',
        contact_status=advertisement.contact_status if advertisement.contact_status else '',
        contact_name=advertisement.contact_name if advertisement.contact_name else '',
        is_historical=is_historical,
        url=str(advertisement.url),
    )

    if advertisement.added_by:
        fio = fill_user_fio_template(advertisement.added_by)
        text += DISPATCHER_USERNAME_TEMPLATE.format(
            fio=fio,
            date=advertisement.added_at.strftime('%d.%m'),
        )

    return text


def get_advertisement_base() -> AdvertisementBase:
    advertisement_base = AdvertisementBase(flat=FlatBase(house=HouseBase()))
    return advertisement_base


async def refresh_advertisement(session: AsyncSession, advertisement: Advertisement) -> Advertisement:
    await session.refresh(advertisement, ['flat'])
    await session.refresh(advertisement, ['added_by'])
    await session.refresh(advertisement.flat, ['house'])
    await session.refresh(advertisement.flat, ['rooms'])
    await session.refresh(advertisement.flat.house, ['flats'])
    return advertisement


async def create_advertisement(session: AsyncSession, advertisement: AdvertisementBase) -> Advertisement:
    if advertisement.flat.house:
        house = await house_service.get_house(session, advertisement.flat.house.cadastral_number)
        if not house:
            if isinstance(advertisement.flat.house, HouseBase):
                house_create = HouseCreate(**advertisement.flat.house.model_dump())
            else:
                house_create = HouseCreate.model_validate(advertisement.flat.house)
            house = await house_service.create_house(session, house_create)
        advertisement.flat.house = house

    rooms = []
    for room in advertisement.flat.rooms:
        room_create = RoomCreate(**room.model_dump())
        room = Room(**room_create.model_dump())
        rooms.append(room)
    advertisement.flat.rooms = rooms

    flat = await flat_service.get_flat(session, advertisement.flat.cadastral_number)
    if not flat:
        flat_create = FlatCreate(**advertisement.flat.model_dump())
        flat = await flat_service.create_flat(session, flat_create)
    advertisement.flat = flat

    advertisement_create = AdvertisementCreate(**advertisement.model_dump())
    advertisement = await advertisement_service.create_advertisement(session, advertisement_create)

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e

    return await refresh_advertisement(session, advertisement)
