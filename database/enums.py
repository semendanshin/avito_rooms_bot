from enum import Enum as pyEnum


class UserRole(pyEnum):
    USER = 'Гость'
    ADMIN = 'Управляющий'
    DISPATCHER = 'Диспетчер'
    AGENT = 'Агент'


class AdvertisementStatus(pyEnum):
    NEW = 'New'
    VIEWED = 'Viewed'
    ASSIGNED = 'Assigned'
    DONE = 'Done'
    CANCELED = 'Canceled'


class RoomType(pyEnum):
    LIVING = 'Ж'
    NON_LIVING = 'Н'
    FOR_RENT = 'С'
    RELATIVE = 'Р'


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


class EntranceType(pyEnum):
    STREET = 'Вх-Ул'
    YARD = 'Вх-Дв'
    ARCH = 'Вх-Ар'
    SEPARATE = 'Вх-Отд'


class EntranceTypeHumanReadable(pyEnum):
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
