from enum import Enum as pyEnum


class CalculateRoomDialogStates(pyEnum):
    PRICE_PER_METER_FOR_SELL = 'price_per_meter_for_sell'
    AGENT_COMMISSION = 'agent_commission'
    PRICE_PER_METER_FOR_BUY = 'price_per_meter_for_buy'
    LIVING_PERIOD = 'living_period'
