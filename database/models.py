from sqlalchemy import Column, Boolean, Enum, Integer, String, DateTime, ForeignKey, Float, BigInteger, Date, Time, ARRAY
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from database.enums import (
    UserRole,
    AdvertisementStatus,
    HouseEntranceType,
    ViewType,
    ToiletType,
    InspectionStatus,
    RoomTypeEnum,
    RoomStatusEnum,
    RoomOwnersEnum,
    RoomRefusalStatusEnum,
    RoomOccupantsEnum,
    FlatEntranceType,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime


Base = declarative_base()


class User(AsyncAttrs, Base):
    __tablename__ = 'user'

    id = Column(BigInteger, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(Enum(UserRole))

    system_first_name = Column(String)
    system_last_name = Column(String)
    system_sur_name = Column(String)
    phone_number = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)

    added_advertisements = relationship('Advertisement', back_populates='added_by', foreign_keys='Advertisement.added_by_id', lazy='select')


class House(AsyncAttrs, Base):
    __tablename__ = 'house'

    cadastral_number = Column(String, primary_key=True)
    street_name = Column(String)
    number = Column(String)
    number_of_flours = Column(Integer)
    is_historical = Column(Boolean)

    created_at = Column(DateTime, default=datetime.utcnow)

    flats = relationship('Flat', back_populates='house', lazy='select')


class Flat(AsyncAttrs, Base):
    __tablename__ = 'flat'

    cadastral_number = Column(String, primary_key=True)
    flat_number = Column(String)
    flat_height = Column(Float)
    number_of_rooms = Column(Integer)
    area = Column(Float)
    flour = Column(Integer)
    plan_telegram_file_id = Column(String)
    elevator_nearby = Column(Boolean)
    under_room_is_living = Column(Boolean)
    house_entrance_type = Column(Enum(HouseEntranceType))
    flat_entrance_type = Column(Enum(FlatEntranceType))
    view_type = Column(ARRAY(Enum(ViewType)))
    windows_count = Column(Integer)
    toilet_type = Column(Enum(ToiletType))

    created_at = Column(DateTime, default=datetime.utcnow)

    house_cadastral_number = Column(String, ForeignKey('house.cadastral_number', ondelete='RESTRICT'))
    house = relationship('House', back_populates='flats', lazy='select')

    rooms = relationship('Room', back_populates='flat', lazy='select')
    advertisements = relationship('Advertisement', back_populates='flat', lazy='select')


class Room(AsyncAttrs, Base):
    __tablename__ = 'room'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    area = Column(Float)
    number_on_plan = Column(String)
    type = Column(Enum(RoomTypeEnum))
    status = Column(Enum(RoomStatusEnum))
    owners = Column(ARRAY(Enum(RoomOwnersEnum)))
    refusal_status = Column(Enum(RoomRefusalStatusEnum))
    comment = Column(String)
    occupants = Column(ARRAY(Enum(RoomOccupantsEnum)))
    buyer_price = Column(Integer)
    seller_price = Column(Integer)

    flat_cadastral_number = Column(String, ForeignKey('flat.cadastral_number', ondelete='RESTRICT'))
    flat = relationship('Flat', back_populates='rooms', lazy='select')

    created_at = Column(DateTime, default=datetime.utcnow)


class Advertisement(AsyncAttrs, Base):
    __tablename__ = 'advertisement'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    url = Column(String)
    room_price = Column(Integer)
    room_area = Column(Float)
    status = Column(Enum(AdvertisementStatus), default=AdvertisementStatus.NEW)
    contact_phone = Column(String)
    contact_status = Column(String)
    contact_name = Column(String)
    description = Column(String)

    ad_creation_date = Column(Date)

    flat_cadastral_number = Column(String, ForeignKey('flat.cadastral_number', ondelete='RESTRICT'))
    flat = relationship('Flat', back_populates='advertisements', foreign_keys=[flat_cadastral_number])

    added_at = Column(DateTime, default=datetime.utcnow)
    added_by_id = Column(BigInteger, ForeignKey('user.id', ondelete='RESTRICT'))
    added_by = relationship('User', back_populates='added_advertisements', foreign_keys=[added_by_id])

    viewed_at = Column(DateTime, nullable=True)
    viewed_by_id = Column(BigInteger, ForeignKey('user.id', ondelete='RESTRICT'))
    # viewed_by = relationship('User', back_populates='viewed_advertisements', foreign_keys=[viewed_by_id])

    pinned_dispatcher_id = Column(BigInteger, ForeignKey('user.id', ondelete='RESTRICT'))
    # pinned_dispatcher = relationship('User', back_populates='viewed_advertisements', foreign_keys=[pinned_dispatcher_id])

    pinned_agent_id = Column(BigInteger, ForeignKey('user.id', ondelete='RESTRICT'))
    # pinned_agent = relationship('User', back_populates='viewed_advertisements', foreign_keys=[pinned_agent_id])


class Inspection(AsyncAttrs, Base):
    __tablename__ = 'inspection'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    inspection_date = Column(Date)
    inspection_period_start = Column(Time)
    inspection_period_end = Column(Time)
    status = Column(Enum(InspectionStatus), default=InspectionStatus.PLANNED)

    contact_phone = Column(String, nullable=False)
    contact_status = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)

    meting_tip_text = Column(String, nullable=True)
    meting_tip_photo_id = Column(String, nullable=True)

    inspected_by_id = Column(BigInteger, ForeignKey('user.id', ondelete='RESTRICT'))
    # inspected_by = relationship('User', back_populates='assigned_advertisements', foreign_keys=[inspected_by_id])

    advertisement_id = Column(BigInteger, ForeignKey('advertisement.id', ondelete='RESTRICT'))
    # advertisement = relationship('Advertisement', back_populates='inspections')
