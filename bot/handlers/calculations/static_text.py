CALCULATING_RESULT_TEMPLATE = """
{address}, кв{flat_number} (КН{cadastral_number}) {is_historical}
эт-{flour}{room_under}/{flours_in_building}-{elevator} {entrance_type} {windows_type} {toilet_type}
S-{flat_area}м2({living_area}={living_area_percent}%) h={flat_height}
{price}тр({price_per_meter}тр/м2)

КВ({price_per_meter_for_buy})={flat_price} -- АН: {agent_commission}%={agent_commission_price}
МБК:{mbk} тр/м2

{rooms_info}
"""