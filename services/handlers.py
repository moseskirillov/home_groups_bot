import html
import json
import logging
import os
import textwrap
import traceback

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database.entities import GroupLeader
from database.models import UserModel
from services.data_service import get_or_create_user, get_all_opened_groups, add_to_group
from services.import_service import import_data
from services.keyboard import start_keyboard, join_to_group_keyboard, another_search_keyboard, \
    search_is_empty_keyboard, send_contact_keyboard, return_to_start_inline_keyboard, return_to_start_keyboard

GO_TO_LOGIN_TEXT = 'Вы не залогинены. Для логина, сначала нажмите /start'
MESSAGE_SENT_TEXT = 'Сообщение отправлено'
CONTACT_SENT_TEXT = 'Отправлен контакт'
YOUTH_ADMIN_ID = os.getenv('YOUTH_ADMIN_ID')


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['in_conversation'] = False

    user: UserModel = UserModel(
        update.effective_chat.first_name,
        update.effective_chat.last_name,
        update.effective_chat.username,
        update.effective_message.chat_id
    )
    await get_or_create_user(user)
    context.user_data['user'] = user

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        parse_mode=ParseMode.HTML,
        text=f'Привет, {update.effective_chat.first_name}!\n'
             f'Чтобы найти домашнюю группу, напишите '
             f'<b>название станции метро</b>, или нажмите одну из кнопок',
        reply_markup=start_keyboard
    )


async def import_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: UserModel = context.user_data.get('user')
    if user:
        await import_data()
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Импорт успешно завершен')
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def search_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('in_conversation'):
        logging.info('В контексте conversation, отменяем поиск')
        return
    user: UserModel = context.user_data.get('user')
    if user:
        found_groups = await get_all_opened_groups(update.message.text)
        if len(found_groups) > 0:
            for group in found_groups:
                group_text = groups_process(group)
                await update.message.reply_text(
                    text=group_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_markup=join_to_group_keyboard
                )
                logging.info('Отправили сообщение с группой')
            await update.message.reply_text(
                text='Чтобы искать на другой станции метро, введите ее название или нажмите на одну из кнопок',
                disable_web_page_preview=True,
                reply_markup=another_search_keyboard
            )
            logging.info('Отправили сообщение с предложением поиска другой группы')
        else:
            logging.info(f'Группы по запросу {update.message.text} не найдены')
            await update.message.reply_text(
                text='К сожалению, на этой станции пока нет домашних групп.\n'
                     'Можете ввести другую станцию метро, '
                     'или посмотреть все домашние группы '
                     '<a href="https://wolrus.org/homegroup">на сайте</a>\n',
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=search_is_empty_keyboard
            )
            logging.info('Отправлено сообщение о том что группы не найдены')
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def open_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info('Сработал handler открытия группы')
    user: UserModel = context.user_data.get('user')
    if user:
        context.chat_data['open_group'] = True
        await update.callback_query.answer()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Нажмите на кнопку чтобы отправить Ваш контакт и лидер служения домашних групп свяжется с Вами',
            reply_markup=send_contact_keyboard
        )
        logging.info('Отправлен запрос на отправку контакта')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=GO_TO_LOGIN_TEXT)


async def search_by_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info('Сработал handler кнопки поиска по названию метро')
    user: UserModel = context.user_data.get('user')
    if user:
        await update.message.reply_text(
            text='Чтобы найти домашнюю группу, напишите <b>название станции метро</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=return_to_start_inline_keyboard
        )
        logging.info(MESSAGE_SENT_TEXT)
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def join_to_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info('Обработка запроса на присоединение к ДГ')
    user: UserModel = context.user_data.get('user')
    if user:
        await update.callback_query.answer()
        elements = update.effective_message.text.split('\n')
        group_info = {}
        for element in elements:
            key, value = element.split(': ', 1)
            key = key.strip()
            group_info[key] = value.strip()
        context.user_data['home_group_leader_name'] = group_info['Лидер']
        context.user_data['home_group_info_text'] = update.effective_message.text
        context.user_data['home_group_is_youth'] = \
            group_info['Возраст'] == 'Молодежные (до 25)' or group_info['Возраст'] == 'Молодежные (после 25)'

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Нажмите на кнопку чтобы отправить Ваш контакт и лидер домашней группы свяжется с Вами',
            reply_markup=send_contact_keyboard
        )
        logging.info('Отправили сообщение с предложением отправить контакт')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=GO_TO_LOGIN_TEXT)
    await update.callback_query.answer()


async def send_contact_response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: UserModel = context.user_data.get('user')
    if user:
        is_open_group = context.chat_data.get('open_group')
        ministry_leader_chat_id = os.getenv('MINISTRY_LEADER')
        if is_open_group:
            await send_open_group_request(update, context, ministry_leader_chat_id)
        else:
            logging.info('Получен запрос на присоединение к ДГ')
            group_leader_name = context.user_data.get('home_group_leader_name')
            group_info_text = context.user_data.get('home_group_info_text')
            logging.info(f'Информация о ДГ: {group_info_text}')
            await update.message.reply_text(
                text='Спасибо! Лидер домашней группы свяжется с Вами',
                reply_markup=return_to_start_keyboard
            )
            logging.info('Отправлено финальное сообщение об обратной связи')
            group_leader: GroupLeader = await add_to_group(
                update.effective_user.id,
                group_leader_name,
                context.user_data.get('home_group_is_youth') or False
            )
            if context.user_data.get('home_group_is_youth'):
                await send_youth_group_request(update, context, group_info_text, group_leader)
            else:
                await send_general_group_request(update, context, group_info_text, group_leader)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=GO_TO_LOGIN_TEXT)


async def return_to_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info('Сработала кнопка возвращения к старту')
    user: UserModel = context.user_data.get('user')
    if user:
        if update.callback_query:
            logging.info('Сработал callback')
            await update.callback_query.answer()

        logging.info('Отправляем сообщение с предложением поиска ДГ')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            parse_mode=ParseMode.HTML,
            text='Чтобы найти домашнюю группу, напишите '
                 '<b>название станции метро</b>, или нажмите одну из кнопок',
            reply_markup=start_keyboard
        )
        logging.info(MESSAGE_SENT_TEXT)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=GO_TO_LOGIN_TEXT)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error('Произошла ошибка при работе бота:', exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    wrapped_traceback = textwrap.wrap(tb_string, width=2048)
    error_message = (
        f'<pre>Произошла ошибка при работе бота\n</pre>'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
    )

    for i, part in enumerate(wrapped_traceback):
        traceback_message = f'<pre>{html.escape(part)}</pre>'
        message = f'{error_message}\n' \
                  f'<pre>Стек-трейс, часть {i + 1} из ' \
                  f'{len(wrapped_traceback)}</pre>\n\n' \
                  f'{traceback_message}'
        await context.bot.send_message(chat_id=os.getenv('ADMIN_ID'), text=message, parse_mode=ParseMode.HTML)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Произошла ошибка при работе бота. Пожалуйста, нажмите /start для новой попытки или попробуйте позже',
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove()
    )


async def send_open_group_request(update: Update, context: ContextTypes.DEFAULT_TYPE, ministry_leader_chat_id: str):
    logging.info('Получен запрос на открытие ДГ')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Спасибо! Лидер служения свяжется с Вами',
        disable_web_page_preview=True,
        reply_markup=return_to_start_keyboard
    )
    logging.info('Отправлено сообщение с информацией об обратной связи')
    await context.bot.send_message(
        chat_id=ministry_leader_chat_id,
        text='Новый человек хочет открыть домашнюю группу. Вот его контакт:\n',
    )
    logging.info('Отправляем сообщение с информацией об открытии ДГ лидеру')
    await context.bot.send_contact(
        chat_id=ministry_leader_chat_id,
        contact=update.message.contact
    )
    logging.info(MESSAGE_SENT_TEXT)
    context.chat_data.clear()
    logging.info('Контекст очищен')


async def send_youth_group_request(update: Update, context: ContextTypes.DEFAULT_TYPE, group_info_text: str,
                                   group_leader: GroupLeader):
    logging.info('Запрос на молодежную ДГ, пересылаем на Яну')
    await context.bot.send_message(
        chat_id=YOUTH_ADMIN_ID,
        text=f'{update.effective_chat.first_name} '
             f'{update.effective_chat.last_name} '
             f'хочет присоединиться к домашней группе \n\n'
             f'Вот информация о группе и контакт человека: \n\n'
             f'{group_info_text}',
        parse_mode=ParseMode.HTML
    )
    logging.info(
        f'Отправлено сообщение Яне о том что к ДГ лидера {group_leader.name} '
        f'хочет присоединиться новый человек '
        f'{update.effective_chat.first_name} {update.effective_chat.last_name}'
    )
    await context.bot.send_contact(
        chat_id=YOUTH_ADMIN_ID,
        contact=update.message.contact
    )
    logging.info(CONTACT_SENT_TEXT)


async def send_general_group_request(update: Update, context: ContextTypes.DEFAULT_TYPE, group_info_text: str,
                                     group_leader: GroupLeader):
    logging.info('Запрос на общую ДГ, пересылаем лидера')
    group_leader_chat_id = group_leader.telegram_id or os.getenv('ADMIN_ID')
    logging.info(f'Получен id чата лидера или админа: {group_leader_chat_id}')
    await context.bot.send_message(
        chat_id=group_leader_chat_id,
        text=f'{update.effective_chat.first_name} '
             f'{update.effective_chat.last_name} '
             f'хочет присоединиться к Вашей домашней группе. '
             f'Вот его/ее контакт:',
    )
    logging.info('Отправлено сообщение лидеру ДГ о том что к нему хочет присоединиться новый человек '
                 f'{update.effective_chat.first_name} {update.effective_chat.last_name}')
    await context.bot.send_contact(
        chat_id=group_leader_chat_id,
        contact=update.message.contact
    )
    logging.info(CONTACT_SENT_TEXT)
    if group_leader is not None and group_leader.region_leader is not None and group_leader.region_leader.telegram_id:
        regional_leader_chat_id = group_leader.region_leader.telegram_id
    else:
        regional_leader_chat_id = os.getenv('ADMIN_ID')
    logging.info(f'Получен id чата регионального лидера или админа: {regional_leader_chat_id}')
    await context.bot.send_message(
        chat_id=regional_leader_chat_id,
        text=f'{update.effective_chat.first_name} '
             f'{update.effective_chat.last_name} '
             f'хочет присоединиться к домашней группе Вашего региона\n\n'
             f'Вот информация о группе и контакт человека: \n\n'
             f'{group_info_text}',
        parse_mode=ParseMode.HTML
    )
    logging.info(
        f'Отправлено сообщение региональному лидеру о том что к ДГ лидера {group_leader.name} '
        f'хочет присоединиться новый человек '
        f'{update.effective_chat.first_name} {update.effective_chat.last_name}')
    await context.bot.send_contact(
        chat_id=regional_leader_chat_id,
        contact=update.message.contact
    )
    logging.info(CONTACT_SENT_TEXT)


def groups_process(group):
    time_str = group.time.strftime('%H:%M')
    home_group = f'Метро: <b>{group.metro}</b>\n' \
                 f'День: <b>{group.day}</b>\nВремя: <b>{time_str}</b>\n' \
                 f'Возраст: <b>{group.age}</b>\n' \
                 f'Тип: <b>{group.type}</b>\n' \
                 f'Лидер: <b>{group.group_leader.name}</b>'
    logging.info(f'Выбранная группа: {home_group}')
    logging.info(f'Лидер группы: {group.group_leader.name}')
    return home_group
