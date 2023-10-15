from dataclasses import dataclass
from typing import Optional


@dataclass
class Result:
    url: str
    price: int
    room_area: float
    number_of_rooms_in_flat: int
    flour: int
    flours_in_building: int
    address: str
    description: str
