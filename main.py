import asyncio
import os
from asyncio import AbstractEventLoop

from telegram.ext import ApplicationBuilder, Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config import logging_init
from database.connection import database_init
from services.conversation import conversation_handler
from services.handlers import start_handler, import_handler, search_group_handler, return_to_start_handler, \
    open_group_handler, search_by_button_handler, join_to_group_handler, send_contact_response_handler, error_handler
from services.keyboard import WRITE_METRO_TEXT

TOKEN = os.getenv('BOT_TOKEN')


def handlers_register(application: Application) -> None:
    application.add_handler(conversation_handler())
    application.add_handler(CommandHandler('start', start_handler))
    application.add_handler(CallbackQueryHandler(return_to_start_handler, pattern='return_to_start'))
    application.add_handler(CallbackQueryHandler(open_group_handler, pattern='open_group'))
    application.add_handler(MessageHandler(filters.Text([WRITE_METRO_TEXT]), search_by_button_handler))
    application.add_handler(CallbackQueryHandler(join_to_group_handler, pattern='join_to_group'))
    application.add_handler(MessageHandler(filters.Text(['Вернуться']), return_to_start_handler))
    application.add_handler(MessageHandler(filters.CONTACT, send_contact_response_handler))
    application.add_handler(CommandHandler('import', import_handler))
    application.add_handler(MessageHandler(filters.TEXT, search_group_handler))
    application.add_error_handler(error_handler)


def main() -> None:
    application: Application = ApplicationBuilder() \
        .token(TOKEN) \
        .read_timeout(300) \
        .write_timeout(300) \
        .build()
    handlers_register(application)
    application.run_webhook(
        listen=os.getenv('LISTEN'),
        port=int(os.getenv('PORT')),
        url_path='',
        webhook_url=os.getenv('URL'),
    )


if __name__ == '__main__':
    logging_init()
    loop: AbstractEventLoop = asyncio.get_event_loop()
    loop.run_until_complete(database_init())
    main()
