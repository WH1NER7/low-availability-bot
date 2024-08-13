from celery import Celery
from associated_advertisement_goods import collect_data
from aiogram import Bot
from aiogram.types import InputFile
import os
import asyncio

celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
# bot = Bot(token=os.getenv('BOT_TOKEN'))


@celery_app.task(name='celery_app.async_task_test')
def async_task_test(x, y):
    return x + y


@celery_app.task(name='celery_app.collect_data_task')
def collect_data_task(company_api_key, api_key, start_date, end_date, authorizev3, cookie, user_agent):
    return collect_data(company_api_key, api_key, start_date, end_date, authorizev3, cookie, user_agent)


@celery_app.task(name='celery_app.on_task_complete')
def on_task_complete(result, chat_id):
    async def send_document():
        bot = Bot(token=os.getenv('BOT_TOKEN'))
        await bot.send_document(chat_id, InputFile(result))

    if not os.path.exists(result):
        raise FileNotFoundError(f"Файл не найден: {result}")

    asyncio.run(send_document())



