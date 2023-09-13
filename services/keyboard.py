from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

RETURN_BUTTON_TEXT = 'Вернуться'
PICK_GROUP_TEXT = 'Подобрать группу'
JOIN_TO_GROUP_TEXT = 'Присоединиться'
SEND_CONTACT_TEXT = 'Отправить контакт'
OPEN_NEW_GROUP_TEXT = 'Открыть свою группу'
WRITE_METRO_TEXT = 'Написать название метро'

start_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton(text=PICK_GROUP_TEXT)],
    [KeyboardButton(text=WRITE_METRO_TEXT)]
], resize_keyboard=True, one_time_keyboard=True)

join_to_group_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton(JOIN_TO_GROUP_TEXT, callback_data='join_to_group')]
])

another_search_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton(text=WRITE_METRO_TEXT)],
    [KeyboardButton(text=PICK_GROUP_TEXT), KeyboardButton(text=RETURN_BUTTON_TEXT)]
], one_time_keyboard=True, resize_keyboard=True)

search_is_empty_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton(OPEN_NEW_GROUP_TEXT, callback_data='open_group')],
    [InlineKeyboardButton(RETURN_BUTTON_TEXT, callback_data='return_to_start')]
])

send_contact_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton(text=SEND_CONTACT_TEXT, request_contact=True), KeyboardButton(text=RETURN_BUTTON_TEXT)]
], resize_keyboard=True)

return_to_start_inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton(text=RETURN_BUTTON_TEXT, callback_data='return_to_start')]
])

return_to_start_keyboard = ReplyKeyboardMarkup([[KeyboardButton(text=RETURN_BUTTON_TEXT)]], resize_keyboard=True)

conversation_days_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton(text='Понедельник'), KeyboardButton(text='Вторник')],
     [KeyboardButton(text='Среда'), KeyboardButton(text='Четверг'), KeyboardButton(text='Пятница')],
     [KeyboardButton(text='Суббота'), KeyboardButton(text='Воскресенье')],
     [KeyboardButton(text=RETURN_BUTTON_TEXT)]],
    one_time_keyboard=True,
    input_field_placeholder='Выберите день недели',
    resize_keyboard=True
)

conversation_age_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton(text='Взрослые')], [KeyboardButton(text='Молодежные (до 25)')],
    [KeyboardButton(text='Молодежные (после 25)')], [KeyboardButton(text=RETURN_BUTTON_TEXT)]
], resize_keyboard=True)

conversation_type_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton(text='Общая'), KeyboardButton(text='Мужская'), KeyboardButton(text='Женская')],
    [KeyboardButton(text='Семейная'), KeyboardButton(text='Тематическая'), KeyboardButton(text='Любая')],
    [KeyboardButton(text=RETURN_BUTTON_TEXT)]
], resize_keyboard=True)

conversation_result_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton(text='Посмотреть результат')]], resize_keyboard=True
)
