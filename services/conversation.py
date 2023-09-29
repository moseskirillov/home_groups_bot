import logging

from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from database.connection import async_session
from database.entities import Group
from database.models import UserModel
from services.handlers import groups_process, GO_TO_LOGIN_TEXT
from services.keyboard import conversation_days_keyboard, conversation_age_keyboard, conversation_type_keyboard, \
    conversation_result_keyboard, start_keyboard, join_to_group_keyboard, search_is_empty_keyboard, RETURN_BUTTON_TEXT, \
    PICK_GROUP_TEXT

DAY, AGE, TYPE, METRO, RESULT = range(5)


def conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Text([PICK_GROUP_TEXT]), conversation_start)],
        states={
            DAY: [MessageHandler(
                filters.Regex("^(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье)$"),
                conversation_day
            )],
            AGE: [MessageHandler(
                filters.Regex("^(Взрослые|Молодежные \(до 25\)|Молодежные \(после 25\))$"),
                conversation_age
            )],
            TYPE: [MessageHandler(
                filters.Regex("^(Общая|Мужская|Женская|Семейная|Тематическая|Любая)$"),
                conversation_type
            )],
            RESULT: [MessageHandler(filters.Text(['Посмотреть результат']), conversation_result)]
        },
        fallbacks=[MessageHandler(filters.Text([RETURN_BUTTON_TEXT]), conversation_cancel)]
    )


async def conversation_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: UserModel = context.user_data.get('user')
    if user:
        logging.info('Начало подбора')
        context.user_data['in_conversation'] = True
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите день недели, в который вы хотели бы посещать домашнюю группу',
            reply_markup=conversation_days_keyboard,
        )
        logging.info('Отправлено сообщение о выборе дня недели')
        return DAY
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def conversation_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: UserModel = context.user_data.get('user')
    if user:
        day = update.message.text
        logging.info(f'Выбран день: {day}')
        context.user_data['day'] = day
        await update.message.reply_text(
            f'Вы выбрали день недели: {day}\n'
            f'Выберите возраст',
            reply_markup=conversation_age_keyboard
        )
        logging.info('Отправлено сообщение о выборе возраста')
        return AGE
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def conversation_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: UserModel = context.user_data.get('user')
    if user:
        day = context.user_data['day']
        age = update.message.text
        logging.info(f'Выбран возраст: {age}')
        context.user_data['age'] = age
        await update.message.reply_text(
            f'Вы выбрали день недели: {day}\n'
            f'Вы выбрали возраст: {age}\n\n'
            f'Выберите тип',
            reply_markup=conversation_type_keyboard
        )
        logging.info('Отправлено сообщение о выборе типа')
        return TYPE
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def conversation_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: UserModel = context.user_data.get('user')
    if user:
        day = context.user_data['day']
        age = context.user_data['age']
        group_type = update.message.text
        logging.info(f'Выбран тип: {type}')
        context.user_data['type'] = group_type
        await update.message.reply_text(
            f'Вы выбрали день недели: <b>{day}</b>\n'
            f'Вы выбрали возраст: <b>{age}</b>\n'
            f'Вы выбрали тип: <b>{group_type}</b>\n\n'
            f'Нажмите на кнопку внизу, чтобы посмотреть результат',
            reply_markup=conversation_result_keyboard,
            parse_mode=ParseMode.HTML
        )
        logging.info('Отправлено сообщение о просмотре результата')
        return RESULT
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def conversation_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: UserModel = context.user_data.get('user')
    if user:
        day = context.user_data['day']
        age = context.user_data['age']
        group_type = context.user_data['type']
        async with async_session() as session:
            if group_type == 'Любая':
                found_groups = (await session.execute(
                    select(Group)
                    .where(Group.is_open)
                    .where(Group.day == day)
                    .where(Group.age == age)
                    .options(joinedload(Group.group_leader)))).scalars().fetchall()
            elif group_type == 'Тематическая':
                found_groups = (await session.execute(
                    select(Group)
                    .where(Group.is_open)
                    .where(Group.day == day)
                    .where(Group.age == age)
                    .where(or_(Group.type == 'Благовестие', Group.type == 'Израильская', Group.type == 'Англоязычная'))
                    .options(joinedload(Group.group_leader)))).scalars().fetchall()
            else:
                found_groups = (await session.execute(
                    select(Group)
                    .where(Group.is_open)
                    .where(Group.day == day)
                    .where(Group.age == age)
                    .where(Group.type == group_type)
                    .options(joinedload(Group.group_leader)))).scalars().fetchall()
            if found_groups:
                logging.info('Найдены группы')
                for group in found_groups:
                    group_text = groups_process(group)
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=group_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=join_to_group_keyboard
                    )
                    logging.info('Отправили сообщение с группой')
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Чтобы искать на другой станции метро, введите ее название или нажмите одну из кнопок',
                    reply_markup=start_keyboard
                )
                logging.info('Отправили сообщение с предложением поиска другой группы')
            else:
                logging.info(f'Группы по запросу, день: {day}, возраст: {age}, тип: {group_type} не найдены')
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='К сожалению, этот поиск не дал результатов.\n'
                         'Можете ввести станцию метро в поиске, '
                         'или посмотреть все домашние группы '
                         '<a href="https://wolrus.org/homegroup">на сайте</a>\n'
                         'Также вы можете связаться с администратором для подбора ближайшей группы',
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_markup=search_is_empty_keyboard
                )
                logging.info('Отправлено сообщение о том что группы не найдены')
        context.user_data['in_conversation'] = False
        logging.info('Выключили conversation')
        return ConversationHandler.END
    else:
        await update.message.reply_text(text=GO_TO_LOGIN_TEXT)


async def conversation_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info('Выбрана отмена подбора')
    context.user_data['in_conversation'] = False
    logging.info('Выключили conversation')
    await update.message.reply_text(
        text='Чтобы найти домашнюю группу, напишите '
             '<b>название станции метро</b>, или нажмите одну из кнопок',
        reply_markup=start_keyboard,
        parse_mode=ParseMode.HTML
    )
    logging.info('Отправили страртовое сообщение')
    return ConversationHandler.END
