import json
import os
import random
from aiogram.types import ParseMode

import bson
from aiogram import Bot, types, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient
import openpyxl

from book_script import book_wh
from free_whs_parser import send_request

API_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
scheduler = AsyncIOScheduler()

client = MongoClient("mongodb://localhost:27017/")
db = client.low_limits_bot
collection = db.book_tasks

user_ids_file = 'user_ids.txt'
user_ids_whs = [615742233, 1080039077, 5498524004, 6699748340, 6365718854]

EXCEL_DIR = 'book_excel'
if not os.path.exists(EXCEL_DIR):
    os.makedirs(EXCEL_DIR)

# Список складов
warehouses = [
    ("Коледино", 507), ("Новосибирск", 686), ("Хабаровск", 1193),
    ("Подольск", 117501), ("Казань", 117986), ("Электросталь", 120762),
    ("Астана", 204939), ("Белые столбы", 206236), ("Тула", 206348),
    ("Пушкино", 207743), ("Невинномысск", 301562), ("Алматы Атакент", 218987),
    ("Санкт-Петербург (Уткина Заводь)", 2737), ("Краснодар (Тихорецкая)", 130744),
    ("Екатеринбург - Испытателей 14г", 1733), ("Екатеринбург - Перспективный 12/2", 300571)
]


async def send_notifications():
    with open(user_ids_file, 'r') as users_file:
        user_ids = set(int(line.strip()) for line in users_file)

    with open('data_file.json', 'r', encoding='utf-8') as file: ## with open('/home/dan/bots/flask_new/output_file.json', 'r', encoding='utf-8') as file:

        data = json.load(file)

    for user_id in user_ids:
        for category, products in data.items():
            if category.startswith("no available"):
                platform = "Wilberries" if "wb" in category else "Ozon"
                title = f"*Нет наличия или скоро закончится по {platform}:*"
                message = ""

                for product, quantity in products.items():
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

    with open(user_ids_file, 'r') as users_file:
        existing_user_ids = set(int(line.strip()) for line in users_file)

    if user_id not in existing_user_ids:
        with open(user_ids_file, 'a') as users_file:
            users_file.write(str(user_id) + '\n')

        await message.reply("Привет! Теперь вы будете получать уведомления.")
    else:
        await message.reply("Вы уже подписаны на уведомления.")

    if user_id in user_ids_whs:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Бронь поставки"), types.KeyboardButton("Удалить задачу на поставку"))
        await message.answer("Выберите действие:", reply_markup=keyboard)


class BookFSM(StatesGroup):
    choose_date_range = State()
    input_date_range = State()
    input_date = State()
    input_excel = State()
    choose_warehouse = State()


def validate_date(date_text):
    try:
        current_date = datetime.now()
        if "-" in date_text:
            start_date, end_date = date_text.split("-")
            start_date = datetime.strptime(start_date.strip(), '%d.%m.%Y')
            end_date = datetime.strptime(end_date.strip(), '%d.%m.%Y')
            if start_date < current_date or end_date < current_date:
                return False
        else:
            date = datetime.strptime(date_text.strip(), '%d.%m.%Y')
            if date < current_date:
                return False
        return True
    except ValueError:
        return False


def validate_excel(file):
    try:
        workbook = openpyxl.load_workbook(file)
        sheet = workbook.active
        for row in sheet.iter_rows(min_row=2, max_col=2, values_only=True):
            barcode, quantity = row
            if barcode is None and quantity is None:
                continue  # Игнорировать пустые строки
            if not isinstance(barcode, (int, float)) or not isinstance(quantity, (int, float)):
                print(f"Invalid row: {row}")
                return False
        return True
    except Exception as e:
        print(e)
        return False


def generate_random_number():
    return random.randint(1000000, 9999999)


@dp.message_handler(lambda message: message.text == "Удалить задачу на поставку", state="*")
async def delete_booking_task(message: types.Message):
    user_id = message.from_user.id

    # Проверяем, является ли пользователь одним из управляющих складами
    if user_id not in user_ids_whs:
        await message.answer("У вас нет прав для выполнения этой операции.")
        return

    # Извлекаем задачи из БД с статусом "В процессе"
    tasks = list(collection.find({"status": "В процессе"}))

    if len(tasks) == 0:
        await message.answer("Нет задач на бронирование поставки в процессе.")
        return

    # Создаем клавиатуру с вариантами задач для удаления
    keyboard = InlineKeyboardMarkup()
    for task in tasks:
        keyboard.add(InlineKeyboardButton(
            f"{task['start_date']} - {task['end_date']} (Склад: {task['warehouse_name']})",
            callback_data=str(task['_id'])
        ))
    print(keyboard.values)
    await message.answer("Выберите задачу для удаления:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: bson.ObjectId.is_valid(c.data))
async def process_delete_task(callback_query: types.CallbackQuery):
    task_id = ObjectId(callback_query.data)
    task = collection.find_one({"_id": task_id})

    if task:
        collection.delete_one({"_id": task_id})
        await bot.send_message(callback_query.from_user.id,
                               f"Задача на {task['start_date']} - {task['end_date']} удалена.")
    else:
        await bot.send_message(callback_query.from_user.id, "Задача не найдена.")

    await callback_query.answer()


@dp.message_handler(lambda message: message.text == "Бронь поставки", state="*")
async def start_booking(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Диапазон дат", callback_data='range'),
                 InlineKeyboardButton("Конкретная дата", callback_data='single'))
    await BookFSM.choose_date_range.set()
    await message.answer("Выберите тип даты:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data in ['range', 'single'], state=BookFSM.choose_date_range)
async def process_date_type(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['date_type'] = callback_query.data
    if callback_query.data == 'range':
        await BookFSM.input_date_range.set()
        await bot.send_message(callback_query.from_user.id, "Введите дату в формате dd.mm.yyyy-dd.mm.yyyy")
    else:
        await BookFSM.input_date.set()
        await bot.send_message(callback_query.from_user.id, "Введите дату в формате dd.mm.yyyy")
    await callback_query.answer()


@dp.message_handler(lambda message: validate_date(message.text), state=[BookFSM.input_date_range, BookFSM.input_date])
async def process_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['date'] = message.text
    await BookFSM.input_excel.set()
    await message.answer("Пришлите Excel файл с товарами.")


@dp.message_handler(content_types=[ContentType.DOCUMENT], state=BookFSM.input_excel)
async def process_excel(message: types.Message, state: FSMContext):
    document_id = message.document.file_id
    file = await bot.get_file(document_id)
    file_path = file.file_path
    file_name = file_path.split("/")[-1]
    file_name = os.path.join(EXCEL_DIR, file_name)

    try:
        # Проверка на дублирование файла
        if collection.find_one({"file_name": file_name}):
            await message.answer(
                "Файл с таким названием уже существует. Пожалуйста, переименуйте файл и попробуйте снова.")
            return

        # Скачивание файла
        await bot.download_file(file_path, file_name)
        print(f"Файл {file_name} загружен и сохранен.")

        # Проверка валидности файла
        if validate_excel(file_name):
            async with state.proxy() as data:
                data['file_name'] = file_name
                data['user_name'] = message.from_user.username

            # Создаем клавиатуру с вариантами складов
            keyboard = InlineKeyboardMarkup()
            for warehouse in warehouses:
                keyboard.add(InlineKeyboardButton(warehouse[0], callback_data=str(warehouse[1])))
            await BookFSM.choose_warehouse.set()
            await message.answer("Выберите склад:", reply_markup=keyboard)
        else:
            await message.answer(
                "Некорректный файл. Убедитесь, что он не пустой и содержит два столбца: баркод и количество.")
    except Exception as e:
        print(f"Ошибка при обработке Excel файла: {e}")
        await message.answer("Произошла ошибка при обработке файла. Пожалуйста, попробуйте снова.")


@dp.callback_query_handler(lambda c: c.data.isdigit(), state=BookFSM.choose_warehouse)
async def process_warehouse(callback_query: types.CallbackQuery, state: FSMContext):
    warehouse_id = int(callback_query.data)
    warehouse_name = next((name for name, id in warehouses if id == warehouse_id), None)

    if warehouse_name is None:
        await bot.send_message(callback_query.from_user.id, "Ошибка: склад не найден.")
        return

    async with state.proxy() as data:
        date_type = data['date_type']
        date = data['date']
        user_name = data['user_name']
        file_name = data['file_name']

        if date_type == "range":
            start_date, end_date = date.split("-")
            start_date = datetime.strptime(start_date.strip(), '%d.%m.%Y')
            end_date = datetime.strptime(end_date.strip(), '%d.%m.%Y')
        else:
            start_date = end_date = datetime.strptime(date.strip(), '%d.%m.%Y')

        task_number = generate_random_number()  # Генерация случайного номера задачи

        task = {
            "task_number": task_number,
            "start_date": start_date,
            "end_date": end_date,
            "user_name": user_name,
            "file_name": file_name,
            "warehouse_name": warehouse_name,
            "warehouse_id": warehouse_id,
            "status": "В процессе",
            "supply_id": 0
        }

        # Добавление задачи в базу данных
        collection.insert_one(task)
        print(f"Задача создана: {task}")

    await bot.send_message(callback_query.from_user.id, f"Задача на бронирование создана. Номер задачи: {task_number}")
    await state.finish()
    await callback_query.answer()


async def notify_users(message, user_ids):
    for user_id in user_ids:
        await bot.send_message(user_id, message, parse_mode=ParseMode.HTML)


async def send_booking_info():
    successful_bookings, errors = book_wh()
    for booking in successful_bookings:
        message = f"Поставка {booking['supply_id']} создана. Дата: {booking['date_range']}. {booking['warehouse_name']}."
        await notify_users(message, booking['user_ids'])

    if errors:
        for error in errors:
            await bot.send_message(615742233, error, parse_mode=ParseMode.HTML)


def run_bot():
    scheduler.start()
    executor.start_polling(dp, loop=asyncio.get_event_loop())


if __name__ == '__main__':
    dp.register_message_handler(on_start, commands=['start'])

    scheduler.add_job(send_notifications, 'cron', hour=9, minute=0)
    scheduler.add_job(send_notifications, 'cron', hour=14, minute=0)
    scheduler.add_job(send_notifications, 'cron', hour=17, minute=0)

    scheduler.add_job(send_free_whs, 'interval', minutes=2)
    scheduler.add_job(send_booking_info, 'interval', seconds=30)

    run_bot()
