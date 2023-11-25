from pydantic import BaseModel, ConfigDict, field_validator, Field
from database.enums import UserRole, AdvertisementStatus, ToiletType, HouseEntranceType, ViewType, FlatEntranceType, \
    RoomTypeEnum, RoomStatusEnum, RoomOwnersEnum, RoomRefusalStatusEnum, RoomOccupantsEnum
from database.models import Room, Advertisement, User, Flat, House
from sqlalchemy.orm.collections import InstrumentedList
from datetime import datetime, date
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class UserBase(BaseModel):
    id: Optional[int]
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER

    system_first_name: Optional[str] = None
    system_last_name: Optional[str] = None
    system_sur_name: Optional[str] = None
    phone_number: Optional[str] = None

    created_at: Optional[datetime] = None


class UserCreate(UserBase):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER

    system_first_name: Optional[str] = None
    system_last_name: Optional[str] = None
    system_sur_name: Optional[str] = None
    phone_number: Optional[str] = None


class UserResponse(UserBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole

    system_first_name: Optional[str] = None
    system_last_name: Optional[str] = None
    system_sur_name: Optional[str] = None
    phone_number: Optional[str] = None

    created_at: datetime


class RoomBase(BaseModel):
    area: Optional[float] = None
    number_on_plan: Optional[str] = None
    type: Optional[RoomTypeEnum] = None
    status: Optional[RoomStatusEnum] = None
    owners: Optional[list[RoomOwnersEnum]] = None
    refusal_status: Optional[RoomRefusalStatusEnum] = None
    occupants: Optional[list[RoomOccupantsEnum]] = None
    comment: Optional[str] = None
    seller_price: Optional[int] = None
    buyer_price: Optional[int] = None


class RoomCreate(RoomBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    area: float
    number_on_plan: str
    type: RoomTypeEnum
    status: RoomStatusEnum
    owners: list[RoomOwnersEnum]
    refusal_status: RoomRefusalStatusEnum
    occupants: list[RoomOccupantsEnum]
    comment: str


class RoomResponse(RoomBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    id: int
    area: float
    number_on_plan: str
    type: RoomTypeEnum
    status: Optional[RoomStatusEnum] = None
    owners: list[RoomOwnersEnum] = []
    refusal_status: Optional[RoomRefusalStatusEnum] = None
    occupants: list[RoomOccupantsEnum] = []
    comment: Optional[str]
    seller_price: Optional[int] = None
    buyer_price: Optional[int] = None


class HouseBase(BaseModel):
    cadastral_number: Optional[str] = None
    street_name: Optional[str] = None
    number: Optional[str] = None
    number_of_flours: Optional[int] = None
    is_historical: Optional[bool] = None


class HouseCreate(HouseBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    cadastral_number: str
    street_name: str
    number: str
    number_of_flours: int
    is_historical: bool


class HouseResponse(HouseBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    cadastral_number: str
    street_name: str
    number: str
    number_of_flours: int
    is_historical: bool


class FlatBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cadastral_number: Optional[str] = None
    flat_number: Optional[str] = None
    flat_height: Optional[float] = None
    number_of_rooms: Optional[int] = None
    area: Optional[float] = None
    flour: Optional[int] = None
    plan_telegram_file_id: Optional[str] = None
    elevator_nearby: Optional[bool] = None
    under_room_is_living: Optional[bool] = None
    house_entrance_type: Optional[HouseEntranceType] = None
    flat_entrance_type: Optional[FlatEntranceType] = None
    view_type: list[ViewType] = []
    windows_count: Optional[int] = None
    toilet_type: Optional[ToiletType] = None

    rooms: list[RoomBase | Room] = []
    house: Optional[HouseBase | Room] = None


class FlatCreate(FlatBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    cadastral_number: str
    flat_number: str
    flat_height: float
    number_of_rooms: int
    area: float
    flour: int
    plan_telegram_file_id: str
    elevator_nearby: bool
    under_room_is_living: bool
    house_entrance_type: HouseEntranceType
    flat_entrance_type: FlatEntranceType
    view_type: list[ViewType]
    windows_count: int
    toilet_type: ToiletType

    rooms: list[Room]
    house: Optional[House] = None


class FlatResponse(FlatBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    cadastral_number: str
    flat_number: str
    flat_height: float
    number_of_rooms: int
    area: float
    flour: int
    plan_telegram_file_id: str
    elevator_nearby: bool
    under_room_is_living: bool
    house_entrance_type: HouseEntranceType
    flat_entrance_type: FlatEntranceType
    view_type: list[ViewType]
    windows_count: int
    toilet_type: ToiletType

    rooms: list[RoomResponse]
    house: HouseResponse

    @field_validator('rooms', mode='before')
    def validate_rooms(cls, v, values):
        if isinstance(v, InstrumentedList):
            return [RoomResponse.model_validate(room) for room in v]
        return v

    @field_validator('house', mode='before')
    def validate_house(cls, v, values):
        if isinstance(v, House):
            return HouseResponse.model_validate(v)
        return v


class AdvertisementBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: Optional[str] = None
    room_price: Optional[int] = None
    room_area: Optional[float] = None
    status: Optional[AdvertisementStatus] = None
    contact_phone: Optional[str] = None
    contact_status: Optional[str] = None
    contact_name: Optional[str] = None
    description: Optional[str] = None

    ad_creation_date: Optional[date] = None

    flat: Optional[FlatBase | Flat] = None

    added_by: Optional[User] = None
    added_at: Optional[datetime] = None


class AdvertisementCreate(AdvertisementBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    url: str
    room_price: int
    room_area: float
    contact_phone: str
    contact_status: str
    contact_name: str
    description: str

    ad_creation_date: Optional[date] = None

    flat: Flat

    added_by: User


class AdvertisementResponse(AdvertisementBase):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    id: int
    url: str
    room_price: int
    room_area: float
    status: AdvertisementStatus
    contact_phone: str
    contact_status: str
    contact_name: str
    description: str

    ad_creation_date: Optional[date] = None

    flat: FlatResponse

    added_by: UserResponse
    added_at: datetime

    @field_validator('flat', mode='before')
    def validate_flat(cls, v, values):
        if isinstance(v, Flat):
            return FlatResponse.model_validate(v)
        return v

    @field_validator('added_by', mode='before')
    def validate_added_by(cls, v, values):
        if isinstance(v, User):
            return UserResponse.model_validate(v)
        return v
