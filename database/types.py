from pydantic import BaseModel, ConfigDict, field_validator, Field
from .enums import UserRole, AdvertisementStatus, ToiletType, EntranceType, ViewType, RoomType
from .models import Room, Advertisement, User, RoomInfo
from sqlalchemy.orm.collections import InstrumentedList
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True, arbitrary_types_allowed=True)

    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    role: UserRole

    system_first_name: Optional[str]
    system_last_name: Optional[str]
    system_sur_name: Optional[str]
    phone_number: Optional[str]


class RoomInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True, arbitrary_types_allowed=True)

    number: int
    area: float
    status: RoomType
    description: str


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True, arbitrary_types_allowed=True)

    id: int
    room_area: float
    flat_area: float
    number_of_rooms_in_flat: int
    flour: int
    flours_in_building: int
    address: str
    plan_telegram_file_id: str
    flat_number: str
    flat_height: float
    cadastral_number: str
    house_is_historical: bool
    elevator_nearby: bool
    under_room_is_living: bool
    entrance_type: EntranceType
    view_type: ViewType
    toilet_type: ToiletType

    rooms_info: Optional[list[RoomInfoResponse]] = Field()

    created_at: datetime

    @field_validator('rooms_info', mode='before')
    def check_room_info(cls, v, values):
        if isinstance(v, InstrumentedList):
            answer = [RoomInfoResponse.model_validate(el) for el in v]
            return answer
        return v


class AdvertisementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True, arbitrary_types_allowed=True)

    advertisement_id: int = Field(alias='id')
    url: str
    price: int
    status: AdvertisementStatus
    contact_phone: str
    contact_status: str
    contact_name: str
    description: str

    room: RoomResponse = Field()

    added_at: datetime
    added_by: UserResponse = Field()

    viewed_at: Optional[datetime]
    viewed_by_id: Optional[int]

    @field_validator('room', mode='before')
    def check_room(cls, v, values):
        if isinstance(v, Room):
            return RoomResponse.model_validate(v, from_attributes=True)
        return v

    @field_validator('added_by', mode='before')
    def check_added_by(cls, v, values):
        if isinstance(v, User):
            return UserResponse.model_validate(v, from_attributes=True)
        return v


class UserCreate(BaseModel):
    id: int
    username: Optional[str] = ''
    first_name: Optional[str] = ''
    last_name: Optional[str] = ''
    system_first_name: Optional[str] = ''
    system_last_name: Optional[str] = ''
    system_sur_name: Optional[str] = ''
    phone_number: Optional[str] = ''

    role: UserRole = UserRole.USER


class RoomInfoCreate(BaseModel):
    number: int
    area: float
    status: RoomType
    description: str

    class Config:
        orm_mode = True


class RoomCreate(BaseModel):
    id: int
    room_area: float
    flat_area: Optional[float]
    number_of_rooms_in_flat: int
    flour: int
    flours_in_building: int
    address: str
    plan_telegram_file_id: str
    flat_number: Optional[str]
    flat_height: Optional[float]
    cadastral_number: Optional[str]
    house_is_historical: Optional[bool]
    elevator_nearby: Optional[bool]
    under_room_is_living: Optional[bool]
    entrance_type: Optional[EntranceType]
    view_type: Optional[ViewType]
    toilet_type: Optional[ToiletType]

    class Config:
        orm_mode = True


class AdvertisementCreate(BaseModel):
    url: str
    price: int
    status: AdvertisementStatus = AdvertisementStatus.NEW
    contact_phone: str
    contact_status: str
    contact_name: str
    description: str

    room_id: int

    added_by_id: int

    class Config:
        orm_mode = True


class DataToGather(BaseModel):
    url: Optional[str] = None
    price: Optional[int] = None
    status: AdvertisementStatus = AdvertisementStatus.NEW
    contact_phone: Optional[str] = None
    contact_status: Optional[str] = None
    contact_name: Optional[str] = None
    description: Optional[str] = None

    room_id: Optional[int] = None

    added_by_id: Optional[int] = None

    room_area: Optional[float] = None
    flat_area: Optional[float] = None
    number_of_rooms_in_flat: Optional[int] = None
    flour: Optional[int] = None
    flours_in_building: Optional[int] = None
    address: Optional[str] = None
    plan_telegram_file_id: Optional[str] = None
    flat_number: Optional[str] = None
    flat_height: Optional[float] = None
    cadastral_number: Optional[str] = None
    house_is_historical: Optional[bool] = None
    elevator_nearby: Optional[bool] = None
    room_under_is_living: Optional[bool] = None
    entrance_type: Optional[EntranceType] = None
    view_type: Optional[ViewType] = None
    toilet_type: Optional[ToiletType] = None

    rooms_info: Optional[list[RoomInfoCreate]] = []