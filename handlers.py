from aiogram import types
from celery_app import collect_data_task, on_task_complete
from datetime import datetime, timedelta
import os


async def send_data(message: types.Message):
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    api_key = os.getenv('API_TOKEN')
    authorizev3 = os.getenv('authorizev3')
    cookie = os.getenv('COOKIE')
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/124.0.0.0 YaBrowser/24.6.0.0 Safari/537.36"
    company_api_key = os.getenv("MYK_API_KEY")
    await message.reply("Данные собираются, это может занять некоторое время...")

    task = collect_data_task.apply_async(
        args=[company_api_key, api_key, start_date, end_date, authorizev3, cookie, user_agent],
        link=on_task_complete.s(message.chat.id)
    )
