import json
import os

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from datetime import datetime, timedelta

from free_whs_parser import send_request

API_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Здесь вставьте список пользовательских ID
# user_ids = [615742233]

user_ids_file = 'user_ids.txt'
user_ids_whs = [615742233, 1080039077, 5498524004, 6699748340, 6365718854]
# Загружаем данные из файла


async def send_notifications():
    with open(user_ids_file, 'r') as users_file:
        user_ids = set(int(line.strip()) for line in users_file)

    with open('data_file.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    for user_id in user_ids:
        for category, products in data.items():
            # Проверяем, что категория начинается с "no available"
            if category.startswith("no available"):
                platform = "Wilberries" if "wb" in category else "Ozon"
                title = f"*Нет наличия или скоро закончится по {platform}:*"
                message = ""

                for product, quantity in products.items():
                    # Экранируем символы Markdown
                    product = product.replace('_', '\_').replace('*', '\*')
                    message += f"\n{product}: {quantity}"

                full_message = f"{title}{message}"
                try:
                    await bot.send_message(user_id, full_message, parse_mode=types.ParseMode.MARKDOWN)
                except:
                    pass


async def send_free_whs():
    data = send_request()

    if data:
        for user_id in user_ids_whs:
            try:
                await bot.send_message(user_id, data, parse_mode=types.ParseMode.MARKDOWN)
            except Exception as e:
                print(e)


async def on_start(message: types.Message):
    user_id = message.from_user.id

    # Проверяем, есть ли уже такой id в файле
    with open(user_ids_file, 'r') as users_file:
        existing_user_ids = set(int(line.strip()) for line in users_file)

    if user_id not in existing_user_ids:
        # Если такого id нет, то записываем его в файл
        with open(user_ids_file, 'a') as users_file:
            users_file.write(str(user_id) + '\n')

        await message.reply("Привет! Теперь вы будете получать уведомления.")
    else:
        await message.reply("Вы уже подписаны на уведомления.")


def run_bot():
    scheduler.start()
    executor.start_polling(dp, loop=asyncio.get_event_loop())


if __name__ == '__main__':
    dp.register_message_handler(on_start, commands=['start'])

    # Задаем задачи по расписанию
    scheduler.add_job(send_notifications, 'cron', hour=9, minute=0)
    scheduler.add_job(send_notifications, 'cron', hour=14, minute=0)
    scheduler.add_job(send_notifications, 'cron', hour=17, minute=0)

    scheduler.add_job(send_free_whs, 'interval', minutes=1)

    run_bot()
