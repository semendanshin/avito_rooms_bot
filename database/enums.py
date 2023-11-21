from enum import Enum as pyEnum


class UserRole(pyEnum):
    USER = 'Гость'
    ADMIN = 'Руководитель'
    DISPATCHER = 'Диспетчер'
    AGENT = 'Агент'


class AdvertisementStatus(pyEnum):
    NEW = 'New'
    CANCELED = ' НЕТ'
    VIEWED = 'СМ'
    ASSIGNED = 'ПОК'
    MAYBE = 'ДР'
    DONE = 'РЕЗ'
    CANCELED_AFTER_VIEW = 'ОТК'
    BARGAIN = 'ТОРГ'
    AGREED = 'ЗАД'
    BOUGHT = 'КУП'


class RoomStatusEnum(pyEnum):
    LIVING = 'Ж'
    NON_LIVING = 'Н'
    FOR_RENT = 'С'
    RELATIVE = 'Р'
    GOVERNMENT = 'СПб'


class RoomTypeEnum(pyEnum):
    LIVING = 'ЖИЛ'
    MOP = 'МОП'
    KITCHEN = 'КУХ'
    BATHROOM = 'СУ'
    CLOSET = 'ШК'


class RoomOwnersEnum(pyEnum):
    MALE = 'М'
    FEMALE = 'Ж'
    OLD = 'Пенс'


class RoomRefusalStatusEnum(pyEnum):
    ROOM_ON_DIRECT_SALE = 'ПП'
    ROOM_ON_CROSS_SALE = 'ВСТ'
    OTHER_ROOM_OF_SELLER = 'СОБ'
    WRITTEN = 'ПИС'
    NOTARY = 'НОТ'
    NO = 'нет'


class RoomOccupantsEnum(pyEnum):
    MALE = 'М'
    FEMALES = 'Ж'
    OLD = 'Пенс'
    KIDS = 'Дети'
    RELATIVES = 'Род'
    ANIMALS = 'Жив'


class ToiletType(pyEnum):
    COMBINED = 'СУ-С'
    SEPARATE = 'СУ-Р'
    WITHOUTBATH = 'СУ-БВ'
    SHOWERONKITCHEN = 'СУ-ДК'


class ToiletTypeHumanReadable(pyEnum):
    COMBINED = 'Совмещенный'
    SEPARATE = 'Раздельный'
    WITHOUTBATH = 'Без ванны'
    SHOWERONKITCHEN = 'Душ на кухне'


class FlatEntranceType(pyEnum):
    KITCHEN = 'Кух'
    ONE = 'Один'
    TWO = 'Два'


class HouseEntranceType(pyEnum):
    STREET = 'Вх-Ул'
    YARD = 'Вх-Дв'
    ARCH = 'Вх-Ар'
    SEPARATE = 'Вх-Отд'


class HouseEntranceTypeHumanReadable(pyEnum):
    STREET = 'Вход с улицы'
    YARD = 'Вход с двора'
    ARCH = 'Вход через арку'
    SEPARATE = 'Отдельный вход'


class ViewType(pyEnum):
    STREET = 'Ок-Ул'
    YARD = 'Ок-Дв'
    PARK = 'Ок-Вид'


class ViewTypeHumanReadable(pyEnum):
    STREET = 'Вид на улицу'
    YARD = 'Вид во двор'
    PARK = 'Вид на парк'


class InspectionStatus(pyEnum):
    PLANNED = 'Запланирован'
    DONE = 'Проведен'
    CANCELED = 'Отменен'
