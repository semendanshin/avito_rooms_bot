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
    # "Санузел в квартире какой? и кнопки вариантов [Совмещенный] [Раздельный] [Без ванны] [Душ на кухне]"
#  - вывод СУ-Р или СУ-С или СУ-БВ или СУ-ДК
    COMBINED = 'СУ-Р'
    SEPARATE = 'СУ-С'
    WITHOUTBATH = 'СУ-БВ'
    SHOWERONKITCHEN = 'СУ-ДК'


# "Вход в парадную откуда? и кнопки вариантов [С улицы] [Со двора] [В арке] [Отдельный]"
#  - вывод Вх-Ул или Вх-Дв или Вх-Ар или Вх-Отд
class EntranceType(pyEnum):
    STREET = 'Вх-Ул'
    YARD = 'Вх-Дв'
    ARCH = 'Вх-Ар'
    SEPARATE = 'Вх-Отд'


# "Окна комнаты выходят куда? и кнопки вариантов [На улицу] [Во двор] [На воду или парк/лес]"
#  - вывод Ок-Ул или Ок-Дв или Ок-Вид
class ViewType(pyEnum):
    STREET = 'Ок-Ул'
    YARD = 'Ок-Дв'
    PARK = 'Ок-Вид'
