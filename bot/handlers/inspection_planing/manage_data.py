from enum import Enum as pyEnum
from datetime import time


class InspectionPlaningConversationSteps(pyEnum):
    GET_DATE = 'get_date'
    GET_TIME = 'get_time'
    GET_CONTACT_INFO = 'get_contact_info'
    GET_METING_TIP = 'get_meting_tip'
    CONFIRM = 'confirm'
    CANCEL = 'cancel'


class InspectionTimePeriods(pyEnum):
    p1 = (time(18, 30), time(19, 30))
    p2 = (time(19, 0), time(20, 0))
    p3 = (time(19, 30), time(20, 30))
    p4 = (time(20, 0), time(21, 0))
    p5 = (time(12, 0), time(14, 0))
