from enum import Enum as pyEnum


class AdminAddAdvertisementConversationSteps(pyEnum):
    """Enum for steps in AdminAddAdvertisementConversation"""
    ADD_URL = 1
    CONFIRM_ADDRESS = 2
    ADD_FLAT_NUMBER = 3
    FLAT_ALREADY_EXISTS = 4
    CHOOSE_DISPATCHER = 5
