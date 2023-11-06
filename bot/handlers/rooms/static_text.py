FIRST_ROOM_TEMPLATE = """
{address}, кв{flat_number} (КН{cadastral_number}) {is_historical}
{price}тр({price_per_meter}тр/м2)
эт-{flour}{room_under}/{flours_in_building}-{elevator} {entrance_type} {windows_type} {toilet_type}
S-{flat_area}м2({living_area}={living_area_percent}%) h={flat_height}

{rooms_info}

{contact_phone} {contact_status}-{contact_name}
<a href="{url}">АВИТО</a>"""

DATA_FROM_ADVERTISEMENT_TEMPLATE = """
Комната {room_area} м² в {number_of_rooms_in_flat}-к. кв, {flour}/{flours_in_building} эт.
{address}
{price}тр({price_per_meter}тр/м2)
"""

PARSED_ROOM_TEMPLATE = """
<b>Комната {room_area} м² в {number_of_rooms_in_flat}-к. кв, {flour}/{flours_in_building} эт.</b>
{address}
{price} тр
"""
CONTACT_INFO_TEMPLATE = """
{contact_phone} {contact_status}-{contact_name}
"""
ADDITIONAL_INFO = """
<b>Номер квартиры:</b> {flat_number}
<b>Кадастровый номер:</b> {cadastral_number}
<b>Высота потолков:</b> {flat_height}
<b>Площадь квартиры:</b> {flat_area}
<b>Дом исторический:</b> {house_is_historical}
<b>Лифт рядом:</b> {elevator}
<b>Тип подъезда:</b> {entrance_type}
<b>Вид из окна:</b> {view_type}
<b>Тип санузла:</b> {toilet_type}
<b>Описание комнат:</b> {rooms_info}
"""
AVITO_URL_TEMPLATE = """
<a href="{url}">АВИТО</a>
"""
DISPATCHER_USERNAME_TEMPLATE = """ - {date} {fio}"""
ADMIN_USERNAME_TEMPLATE = """
Оценено пользователем @{username}
"""
AGENT_USERNAME_TEMPLATE = """
Отсмотрено пользователем @{username}
"""
FIO_TEMPLATE = "{first_name} {last_name_letter}{sur_name_letter}"

# SECOND_ROOM_TEMPLATE = """
# <b>Комната {room_area} м² в {number_of_rooms_in_flat}-к. кв, {flour}{room_under}/{flours_in_building} эт.</b>
# <b>Цена:</b> {price} ₽
# <b>Цена за м²:</b> {price_per_meter} ₽
# <b>Адрес:</b> {address}
#
# <b>Номер квартиры:</b> {flat_number}
# <b>Кадастровый номер:</b> {cadastral_number}
# <b>Высота потолков:</b> {flat_height}
# <b>Площадь квартиры:</b> {flat_area} ({living_area}={living_area_percent})м²
# <b>Дом исторический:</b> {house_is_historical}
# <b>Лифт рядом:</b> {elevator}
# <b>Тип подъезда:</b> {entrance_type}
# <b>Вид из окна:</b> {windows_type}
# <b>Тип санузла:</b> {toilet_type}
#
# {rooms_info}
#
# {contact_phone} {contact_status}-{contact_name}
#
# <a href="{url}">Ссылка на объявление</a>
# """