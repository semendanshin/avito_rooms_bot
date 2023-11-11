from enum import Enum
from bot.service import advertisement as advertisement_service
from database.types import DataToGather, UserResponse, RoomInfoCreate
from database.models import User, Advertisement
from .static_text import (FIRST_ROOM_TEMPLATE, PARSED_ROOM_TEMPLATE, CONTACT_INFO_TEMPLATE, ADDITIONAL_INFO,
                          AVITO_URL_TEMPLATE, DATA_FROM_ADVERTISEMENT_TEMPLATE, FIO_TEMPLATE,
                          DISPATCHER_USERNAME_TEMPLATE)

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


def fill_data_from_advertisement_template(data: DataToGather) -> str:
    text = DATA_FROM_ADVERTISEMENT_TEMPLATE.format(
        room_area=data.room_area,
        number_of_rooms_in_flat=data.number_of_rooms_in_flat,
        flour=data.flour,
        flours_in_building=data.flours_in_building,
        address=data.address,
        price=data.price // 1000,
        price_per_meter=int(data.price / data.room_area // 1000),
    )
    text += '\n' + data.description
    return text


def fill_parsed_room_template(data: DataToGather) -> str:
    text = PARSED_ROOM_TEMPLATE.format(
        room_area=data.room_area,
        number_of_rooms_in_flat=data.number_of_rooms_in_flat,
        flour=data.flour,
        flours_in_building=data.flours_in_building,
        address=str(data.address),
        price=data.price // 1000,
    )
    if data.contact_phone:
        text += '\n' + CONTACT_INFO_TEMPLATE.format(
            contact_phone=data.contact_phone,
            contact_status=data.contact_status,
            contact_name=data.contact_name,
        )
    if any([data.__getattribute__(attr) for attr in [
        'flat_number', 'cadastral_number', 'flat_height', 'flat_area',
        'house_is_historical', 'elevator_nearby', 'entrance_type', 'view_type', 'toilet_type', 'rooms_info'
    ]]):
        text += '\n' + ADDITIONAL_INFO.format(
            flat_number=data.flat_number if data.flat_number else '',
            cadastral_number=data.cadastral_number if data.cadastral_number else '',
            flat_height=data.flat_height if data.flat_height else '',
            flat_area=data.flat_area if data.flat_area else '',
            house_is_historical="Да" if data.house_is_historical else "Нет" if data.house_is_historical is not None else "",
            elevator="Да" if data.elevator_nearby else "Нет" if data.elevator_nearby is not None else "",
            entrance_type=data.entrance_type.value if data.entrance_type else '',
            view_type=data.view_type.value if data.view_type else '',
            toilet_type=data.toilet_type.value if data.toilet_type else '',
            rooms_info='\n'.join(
                [
                    f'{room.number}/{room.area}{room.description}'
                    # f'{room.number}/{room.area}-{room.status.value}({room.description})'
                    for room in data.rooms_info
                ]
            ) if data.rooms_info else '',
        )
    text += '\n' + AVITO_URL_TEMPLATE.format(url=data.url)
    return text


def fill_user_fio_template(user: User | UserResponse) -> str:
    return FIO_TEMPLATE.format(
        first_name=user.system_first_name if user.system_first_name else '',
        last_name_letter=user.system_last_name[
            0] if user.system_last_name else '',
        sur_name_letter=user.system_sur_name[0] if user.system_sur_name else '',
    )


def fill_first_room_template(data: DataToGather) -> str:
    living_area = round(sum([room.area for room in data.rooms_info]), 1) if data.rooms_info else ''
    living_area_percent = int(living_area / data.flat_area * 100) if data.flat_area and living_area else ''

    price_per_meter = int(data.price / data.room_area) // 1000 if data.room_area else ''
    price = data.price // 1000

    elevator = 'бл' if data.elevator_nearby is not None and not data.elevator_nearby else ''

    if data.flour and data.flour == 2 and data.under_room_is_living is not None:
        room_under = '(кв)' if data.under_room_is_living else '(н)'
    else:
        room_under = ''

    # f'{room.number}/{room.area}-{room.status.value}({room.description})'
    rooms_info = '\n'.join(
        [
            f'{room.number}/{room.area}{room.description}'
            for room in data.rooms_info
        ]
    ) if data.rooms_info else ''

    text = FIRST_ROOM_TEMPLATE.format(
        address=str(data.address),
        flat_number=data.flat_number if data.flat_number else '',
        cadastral_number=data.cadastral_number if data.cadastral_number else '',
        price=str(price),
        price_per_meter=str(price_per_meter),
        living_area=str(living_area),
        living_area_percent=str(living_area_percent),
        flour=str(data.flour),
        room_under=room_under,
        flours_in_building=data.flours_in_building if data.flours_in_building else '',
        elevator=elevator,
        entrance_type=data.entrance_type.value if data.entrance_type else '',
        windows_type=data.view_type.value if data.view_type else '',
        toilet_type=data.toilet_type.value if data.toilet_type else '',
        flat_area=data.flat_area if data.flat_area else '',
        room_area=data.room_area if data.room_area else '',
        flat_height=data.flat_height if data.flat_height else '',
        rooms_info=rooms_info,
        contact_phone=data.contact_phone if data.contact_phone else '',
        contact_status=data.contact_status if data.contact_status else '',
        contact_name=data.contact_name if data.contact_name else '',
        is_historical='памятник' if data.house_is_historical else '',
        url=str(data.url),
    )

    if data.added_by:
        fio = fill_user_fio_template(data.added_by)
        text += DISPATCHER_USERNAME_TEMPLATE.format(
            fio=fio,
            date=data.added_at.strftime('%d.%m'),
        )

    return text


async def get_data_by_advertisement_id(session: AsyncSession, advertisement_id: int) -> DataToGather:
    advertisement = await advertisement_service.get_advertisement(session, advertisement_id)
    await session.refresh(advertisement, ['room'])
    await session.refresh(advertisement.room, ['rooms_info'])
    await session.refresh(advertisement, ['added_by'])
    return await get_data_by_advertisement(advertisement)


async def get_data_by_advertisement(advertisement: Advertisement) -> DataToGather:
    rooms_info = []
    for room_info in advertisement.room.rooms_info:
       rooms_info.append(
           RoomInfoCreate(
                number=room_info.number,
                status=room_info.status,
                area=room_info.area,
                description=room_info.description,
           )
       )
    data = DataToGather(
        url=advertisement.url,
        price=advertisement.price,
        contact_phone=advertisement.contact_phone,
        contact_status=advertisement.contact_status,
        contact_name=advertisement.contact_name,
        description=advertisement.description,
        room_area=advertisement.room.room_area,
        number_of_rooms_in_flat=advertisement.room.number_of_rooms_in_flat,
        flour=advertisement.room.flour,
        flours_in_building=advertisement.room.flours_in_building,
        address=advertisement.room.address,
        flat_number=advertisement.room.flat_number,
        plan_telegram_file_id=advertisement.room.plan_telegram_file_id,
        cadastral_number=advertisement.room.cadastral_number,
        flat_height=advertisement.room.flat_height,
        flat_area=advertisement.room.flat_area,
        house_is_historical=advertisement.room.house_is_historical,
        elevator_nearby=advertisement.room.elevator_nearby,
        under_room_is_living=advertisement.room.under_room_is_living,
        entrance_type=advertisement.room.entrance_type,
        view_type=advertisement.room.view_type,
        toilet_type=advertisement.room.toilet_type,
        rooms_info=rooms_info,
        added_at=advertisement.added_at,
        added_by=advertisement.added_by,
    )
    return data
