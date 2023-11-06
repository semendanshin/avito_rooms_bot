from enum import Enum


class AddRoleConversationSteps(Enum):
    GET_USERNAME = 10
    GET_ROLE = 20
    CONFIRM_ROLE = 25
    GET_FIO = 30
    GET_PHONE = 40
