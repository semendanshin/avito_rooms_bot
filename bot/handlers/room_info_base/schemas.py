from pydantic import BaseModel, ConfigDict

from telegram import Message
from database.enums import RoomTypeEnum, RoomOccupantsEnum, RoomOwnersEnum, RoomStatusEnum, RoomRefusalStatusEnum
from typing import Optional


class RoomInfoBase(BaseModel):
    room_number: Optional[int] = None
    room_area: Optional[float] = None
    room_type: Optional[RoomTypeEnum] = None
    room_occupants: dict[RoomOccupantsEnum, int] = dict()
    room_owners: dict[RoomOwnersEnum, int] = dict()
    room_status: Optional[RoomStatusEnum] = None
    room_refusal_status: Optional[RoomRefusalStatusEnum] = None
    comment: Optional[str] = ""


class RoomsInfoBase(BaseModel):
    rooms: list[RoomInfoBase]


class RoomsInfoConversationData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    advertisement_id: int
    rooms_info_base: Optional[RoomsInfoBase] = None
    room_info_base: Optional[RoomInfoBase] = None
    rooms_info_base_message: Message
    rooms_info_base_message_id: Optional[int] = None
    effective_ad_message_id: Optional[int] = None
    effective_ad_message: Optional[Message] = None
