from .enums import RoomInfoBaseConversationSteps

ROOM_TEMPLATE = '{number}/{area}-{status}({owners} ={refusal_status}; {comment}) {occupants}'

ROOMS_INFO_TEXT = 'Сведения о комнатах:\n\n'

TEXTS = {
    RoomInfoBaseConversationSteps.PICK_ROOM_TO_DELETE_OR_EDIT: 'Выберите комнату для редактирования/удаления:',
    RoomInfoBaseConversationSteps.ADD_ROOM_NUMBER: 'Введите номер комнаты:',
    RoomInfoBaseConversationSteps.ADD_ROOM_AREA: 'Введите площадь комнаты (пропустить -> /0):',
    RoomInfoBaseConversationSteps.ADD_ROOM_TYPE: 'Выберите тип комнаты:',
    RoomInfoBaseConversationSteps.ADD_ROOM_OCCUPANTS: 'Выберите количество проживающих:',
    RoomInfoBaseConversationSteps.ADD_ROOM_OWNERS: 'Выберите количество собственников:',
    RoomInfoBaseConversationSteps.ADD_ROOM_STATUS: 'Выберите статус комнаты:',
    RoomInfoBaseConversationSteps.ADD_ROOM_REFUSAL_STATUS: 'Выберите статус отказа:',
    RoomInfoBaseConversationSteps.SAVE: 'Сохранить',
    RoomInfoBaseConversationSteps.CANCEL: 'Отмена',
    RoomInfoBaseConversationSteps.START_EDIT_ROOM: 'Редактировать',
    RoomInfoBaseConversationSteps.CHOOSE_DELETE_OR_EDIT: 'Выберите действие:',
    RoomInfoBaseConversationSteps.ADD_ROOM_COMMENT: 'Введите комментарий в свободной форме (пропустить -> /0):',
}
