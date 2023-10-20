from enum import Enum as pyEnum


class UserRole(pyEnum):
    USER = 'User'
    ADMIN = 'Admin'
    DISPATCHER = 'Dispatcher'
    AGENT = 'Agent'


class AdvertisementStatus(pyEnum):
    NEW = 'New'
    VIEWED = 'Viewed'
    ASSIGNED = 'Assigned'
    DONE = 'Done'
    CANCELED = 'Canceled'


class RoomType(pyEnum):
    LIVING = 'Ж'
    NON_LIVING = 'Н'


class ToiletType(pyEnum):
    COMBINED = 'СУ-Р'
    SEPARATE = 'СУ-С'
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
