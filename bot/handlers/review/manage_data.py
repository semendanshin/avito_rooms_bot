from enum import Enum as pyEnum


class ReviewConversationStates(pyEnum):
    CHOOSE_DISPATCHER = 'choose_dispatcher'
    CHOOSE_AGENT = 'choose_agent'
    CONFIRMATION = 'confirmation'
