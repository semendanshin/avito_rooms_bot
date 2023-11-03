from sqlalchemy import Column, Boolean, Enum, Integer, String, DateTime, ForeignKey, Float, BigInteger, Date, Time
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from database.enums import UserRole, AdvertisementStatus, EntranceType, ViewType, RoomType, ToiletType, InspectionStatus
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

    created_at = Column(DateTime, default=datetime.utcnow)

    added_advertisements = relationship('Advertisement', back_populates='added_by', foreign_keys='Advertisement.added_by_id', lazy='select')


class RoomInfo(AsyncAttrs, Base):
    __tablename__ = 'room_info'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    number = Column(Integer)
    status = Column(Enum(RoomType))
    area = Column(Float)
    description = Column(String)

    main_room_id = Column(BigInteger, ForeignKey('room.id', ondelete='RESTRICT'))
    main_room = relationship('Room', back_populates='rooms_info', lazy='select')


class Room(AsyncAttrs, Base):
    __tablename__ = 'room'

    id = Column(BigInteger, primary_key=True)
    room_area = Column(Float)
    flat_area = Column(Float)
    number_of_rooms_in_flat = Column(Integer)
    flour = Column(Integer)
    flours_in_building = Column(Integer)
    address = Column(String)
    plan_telegram_file_id = Column(String)
    flat_number = Column(String)
    flat_height = Column(Float)
    cadastral_number = Column(String)
    house_is_historical = Column(Boolean)
    elevator_nearby = Column(Boolean)
    under_room_is_living = Column(Boolean)
    entrance_type = Column(Enum(EntranceType))
    view_type = Column(Enum(ViewType))
    toilet_type = Column(Enum(ToiletType))

    advertisements = relationship('Advertisement', back_populates='room')
    rooms_info = relationship('RoomInfo', back_populates='main_room')

    created_at = Column(DateTime, default=datetime.utcnow)


class Advertisement(AsyncAttrs, Base):
    __tablename__ = 'advertisement'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    url = Column(String)
    price = Column(Integer)
    status = Column(Enum(AdvertisementStatus))
    contact_phone = Column(String)
    contact_status = Column(String)
    contact_name = Column(String)
    description = Column(String)

    room_id = Column(BigInteger, ForeignKey('room.id', ondelete='RESTRICT'))
    room = relationship('Room', back_populates='advertisements')

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


# class Review(AsyncAttrs, Base):
#     __tablename__ = 'review'
#
#     id = Column(BigInteger, primary_key=True, autoincrement=True)
#     text = Column(String)
#
#     reviewed_at = Column(DateTime, default=datetime.utcnow)
#     reviewed_by_id = Column(BigInteger, ForeignKey('user.id', ondelete='RESTRICT'))
#     reviewed_by = relationship('User', back_populates='reviewed_by', foreign_keys=[reviewed_by_id])
#
#     advertisement_id = Column(BigInteger, ForeignKey('advertisement.id', ondelete='RESTRICT'))
#     # advertisement = relationship('Advertisement', back_populates='reviews')


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
