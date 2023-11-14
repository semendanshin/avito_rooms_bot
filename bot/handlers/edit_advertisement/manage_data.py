from pydantic import BaseModel, ConfigDict, field_validator, Field
from database.enums import UserRole, AdvertisementStatus, ToiletType, HouseEntranceType, ViewType, FlatEntranceType, \
    RoomTypeEnum, RoomStatusEnum, RoomOwnersEnum, RoomRefusalStatusEnum, RoomOccupantsEnum
from bot.schemas.types import RoomBase
from typing import Optional


class DataToGather(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    advertisement_id: Optional[int] = None
    flat_area: Optional[float] = None
    flat_height: Optional[float] = None
    is_historical: Optional[bool] = None
    elevator_nearby: Optional[bool] = None
    under_room_is_living: Optional[bool] = None
    house_entrance_type: Optional[HouseEntranceType] = None
    # flat_entrance_type: Optional[FlatEntranceType] = None
    view_type: list[ViewType] = []
    windows_count: Optional[int] = None
    toilet_type: Optional[ToiletType] = None
