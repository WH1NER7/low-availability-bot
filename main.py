import json
import os
import random
from aiogram.types import ParseMode

from aiogram.contrib.middlewares.logging import LoggingMiddleware

import bson
from aiogram import Bot, types, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from datetime import datetime, timedelta

import requests

from bson import ObjectId
from pymongo import MongoClient
import openpyxl

from book_script import book_wh
from book_warehouse import COLOR_ORDER
from free_whs_parser import send_request
from get_delta_report import ReportDownloader
from report_aggregation import ReportAggregator

API_TOKEN = os.getenv('BOT_TOKEN')
cookie = os.getenv('COOKIE')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
scheduler = AsyncIOScheduler()

client = MongoClient("mongodb://localhost:27017/")
db = client.low_limits_bot
collection = db.book_tasks

user_ids_file = 'user_ids.txt'
user_ids_whs = [615742233, 1080039077, 5498524004, 6699748340, 6365718854]
user_ids_extra = {615742233, 1080039077}

EXCEL_DIR = 'book_excel'
if not os.path.exists(EXCEL_DIR):
    os.makedirs(EXCEL_DIR)


def fetch_warehouse_ids(warehouse_names):
    url = "https://seller-supply.wildberries.ru/ns/sm-supply/supply-manager/api/v1/supply/acceptanceCoefficientsReport"
    headers = {'Content-Type': 'application/json', 'Cookie': cookie}
    body = {
        "params": {
            "dateTo": "2024-06-26T19:00:00.000Z",
            "dateFrom": "2024-06-19T14:26:30.572Z"
        },
        "jsonrpc": "2.0",
        "id": "json-rpc_18"
    }

    response = requests.post(url, headers=headers, json=body)
    data = response.json()
    results = data.get("result", {}).get("report", [])

    unique_warehouses = {}  # Используем словарь для исключения дубликатов

    for item in results:
        if item["acceptanceType"] == 6 and item["warehouseName"] in warehouse_names:
            if item["warehouseName"] not in unique_warehouses:  # Проверяем, есть ли уже такое название в словаре
                unique_warehouses[item["warehouseName"]] = item["warehouseID"]

    # Преобразуем словарь в список кортежей
    warehouse_ids = list(unique_warehouses.items())
    return warehouse_ids


# Здесь список названий складов, для которых тебе нужны ID
warehouse_names = [
    "Коледино", "Новосибирск", "Хабаровск",
    "Подольск", "Казань", "Электросталь",
    "Астана", "Белые Столбы", "Тула",
    "СЦ Пушкино", "Невинномысск", "Алматы Атакент",
    "Санкт-Петербург (Уткина Заводь)", "Краснодар (Тихорецкая)",
    "Екатеринбург - Испытателей 14г", "Екатеринбург - Перспективный 12/2"
]

# Список складов
warehouses = fetch_warehouse_ids(warehouse_names)


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


@dp.message_handler(commands=['start'])
async def on_start(message: types.Message):
    user_id = message.from_user.id

    # Чтение существующих user_id из файла
    try:
        with open(user_ids_file, 'r') as users_file:
            existing_user_ids = set(int(line.strip()) for line in users_file)
    except FileNotFoundError:
        existing_user_ids = set()

    # Добавление нового user_id в файл, если его там нет
    if user_id not in existing_user_ids:
        with open(user_ids_file, 'a') as users_file:
            users_file.write(str(user_id) + '\n')
        await message.reply("Привет! Теперь вы будете получать уведомления.")
    else:
        await message.reply("Вы уже подписаны на уведомления.")

    # Создание клавиатуры в зависимости от user_id
    if user_id in user_ids_whs and user_id in user_ids_extra:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Бронь поставки"), types.KeyboardButton("Удалить задачу на поставку"), types.KeyboardButton("Дельта отчет"))
    elif user_id in user_ids_whs:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Бронь поставки"), types.KeyboardButton("Удалить задачу на поставку"))
    elif user_id in user_ids_extra:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Дельта отчет"))

    await message.answer("Выберите действие:", reply_markup=keyboard)


class BookFSM(StatesGroup):
    choose_date_range = State()
    input_start_date = State()
    input_end_date = State()
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



# Функция для проверки валидности Excel файла
def validate_excel(file_path):
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        valid = True
        invalid_rows = []

        for row in sheet.iter_rows(min_row=2, max_col=2):
            barcode, quantity = row
            if barcode.value is None and quantity.value is None:
                continue  # Игнорировать пустые строки
            if not isinstance(barcode.value, (int, float)) or not isinstance(quantity.value, (int, float)):
                invalid_rows.append(f"Invalid data in row {row[0].row}: Barcode or Quantity is not a number.")
                valid = False

            # Validate cell colors in column B (quantity column)
            fill = quantity.fill
            if fill.start_color and fill.start_color.rgb:
                color = fill.start_color.rgb[-6:]  # Получаем последние 6 символов для hex-кода цвета
                color = "#" + color  # Преобразуем в формат hex
                if color not in COLOR_ORDER:
                    invalid_rows.append(f"Unexpected color {color} found in cell {quantity.coordinate}.")
                    valid = False

        return valid, invalid_rows
    except Exception as e:
        return False, [str(e)]


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
        start_date = task['start_date'].strftime('%Y-%m-%d')
        end_date = task['end_date'].strftime('%Y-%m-%d')
        keyboard.add(InlineKeyboardButton(
            f"{start_date} - {end_date} (Склад: {task['warehouse_name']})",
            callback_data=str(task['_id'])
        ))

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
        await BookFSM.input_start_date.set()

        # Generate inline keyboard with dates for the next 12 days
        keyboard = InlineKeyboardMarkup(row_width=3)
        current_date = datetime.now()
        for i in range(12):
            date = current_date + timedelta(days=i)
            formatted_date = date.strftime('%d.%m.%Y')
            keyboard.insert(InlineKeyboardButton(formatted_date, callback_data=formatted_date))

        await bot.edit_message_text(
            text="Выберите дату начала диапазона:",
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard
        )
    else:
        await BookFSM.input_date.set()

        # Generate inline keyboard with dates for the next 12 days
        keyboard = InlineKeyboardMarkup(row_width=3)
        current_date = datetime.now()
        for i in range(12):
            date = current_date + timedelta(days=i)
            formatted_date = date.strftime('%d.%m.%Y')
            keyboard.insert(InlineKeyboardButton(formatted_date, callback_data=formatted_date))

        await bot.edit_message_text(
            text="Выберите дату:",
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard
        )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data, state=BookFSM.input_start_date)
async def process_start_date(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['start_date'] = callback_query.data

    await BookFSM.input_end_date.set()

    # Generate inline keyboard with dates for the next 12 days from the selected start date
    keyboard = InlineKeyboardMarkup(row_width=3)
    start_date = datetime.strptime(callback_query.data, '%d.%m.%Y')
    for i in range(12):
        date = start_date + timedelta(days=i)
        formatted_date = date.strftime('%d.%m.%Y')
        keyboard.insert(InlineKeyboardButton(formatted_date, callback_data=formatted_date))

    await bot.edit_message_text(
        text="Выберите дату окончания диапазона:",
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data, state=[BookFSM.input_end_date, BookFSM.input_date])
async def process_end_date(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['end_date'] = callback_query.data

    await BookFSM.input_excel.set()
    await bot.edit_message_text(
        text="Пришлите Excel файл с товарами.",
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id
    )
    await callback_query.answer()


@dp.message_handler(lambda message: validate_date(message.text),
                    state=[BookFSM.input_date, BookFSM.input_start_date, BookFSM.input_end_date])
async def process_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['date'] = message.text
    await BookFSM.input_excel.set()
    await bot.send_message(message.chat.id, "Пришлите Excel файл с товарами.")


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
        is_valid, errors = validate_excel(file_name)
        if is_valid:
            async with state.proxy() as data:
                data['file_name'] = file_name
                data['user_name'] = message.from_user.username

            # Создаем клавиатуру с вариантами складов
            keyboard = InlineKeyboardMarkup()
            for warehouse in warehouses:
                keyboard.add(InlineKeyboardButton(warehouse[0], callback_data=str(warehouse[1])))

            await BookFSM.choose_warehouse.set()
            await bot.send_message(message.chat.id, "Выберите склад:", reply_markup=keyboard)
        else:
            error_message = "Некорректный файл.\n\nУбедитесь, что он не пустой и содержит два столбца: баркод и количество.\nТакже проверьте использованные цвета:\n"
            error_message += "\n".join(errors)
            await message.answer(error_message)
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
        user_name = data['user_name']
        file_name = data['file_name']

        if date_type == "range":
            start_date, end_date = data['start_date'], data['end_date']
            start_date = datetime.strptime(start_date.strip(), '%d.%m.%Y')
            end_date = datetime.strptime(end_date.strip(), '%d.%m.%Y')
            date_info = f"Тип бронирования: Диапазон\nДата начала: {start_date.strftime('%d.%m.%Y')}\nДата окончания: {end_date.strftime('%d.%m.%Y')}"
        else:
            start_date = end_date = datetime.strptime(data['end_date'].strip(), '%d.%m.%Y')
            date_info = f"Тип бронирования: Один день\nДата: {start_date.strftime('%d.%m.%Y')}"

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

        await bot.edit_message_text(
            text=f"Задача на бронирование создана.\nНомер задачи: {task_number}\n{date_info}\nСклад: {warehouse_name}",
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id
        )

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

dp.middleware.setup(LoggingMiddleware())

class DeltaFSM(StatesGroup):
    choose_date_range = State()
    input_start_date = State()
    input_end_date = State()
    input_threshold = State()

@dp.message_handler(lambda message: message.text == "Дельта отчет", state="*")
async def choose_date_range(message: types.Message):
    await DeltaFSM.choose_date_range.set()
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Выбрать диапазон дат", callback_data="range"),
        InlineKeyboardButton("7 дней", callback_data="7"),
        InlineKeyboardButton("3 дня", callback_data="3")
    )
    await message.reply(
        text="Выберите диапазон дат или предопределенный период:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data in ['range', '7', '3'], state=DeltaFSM.choose_date_range)
async def process_date_type(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['date_type'] = callback_query.data

    if callback_query.data == 'range':
        await DeltaFSM.input_start_date.set()
        keyboard = InlineKeyboardMarkup(row_width=3)
        current_date = datetime.now()
        for i in range(12):
            date = current_date + timedelta(days=i)
            formatted_date = date.strftime('%d.%m.%Y')
            keyboard.insert(InlineKeyboardButton(formatted_date, callback_data=formatted_date))

        await bot.edit_message_text(
            text="Выберите дату начала диапазона:",
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard
        )
    else:
        period_days = int(callback_query.data)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days - 1)

        await DeltaFSM.input_threshold.set()
        keyboard = InlineKeyboardMarkup(row_width=3)
        for threshold in [20, 30, 40]:
            keyboard.insert(InlineKeyboardButton(str(threshold), callback_data=str(threshold)))

        async with state.proxy() as data:
            data['start_date'] = start_date.strftime('%d.%m.%Y')
            data['end_date'] = end_date.strftime('%d.%m.%Y')

        await bot.edit_message_text(
            text="Выберите порог дельты:",
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard
        )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data, state=DeltaFSM.input_start_date)
async def process_start_date(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['start_date'] = callback_query.data

    await DeltaFSM.input_end_date.set()

    keyboard = InlineKeyboardMarkup(row_width=3)
    start_date = datetime.strptime(callback_query.data, '%d.%m.%Y')
    for i in range(1, 13, 2):  # Генерируем даты, кратные двум
        date = start_date + timedelta(days=i)
        formatted_date = date.strftime('%d.%m.%Y')
        keyboard.insert(InlineKeyboardButton(formatted_date, callback_data=formatted_date))

    await bot.edit_message_text(
        text="Выберите дату окончания диапазона:",
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data, state=DeltaFSM.input_end_date)
async def process_end_date(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['end_date'] = callback_query.data

    await DeltaFSM.input_threshold.set()

    keyboard = InlineKeyboardMarkup(row_width=3)
    for threshold in [20, 30, 40]:
        keyboard.insert(InlineKeyboardButton(str(threshold), callback_data=str(threshold)))

    await bot.edit_message_text(
        text="Выберите порог дельты:",
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data, state=DeltaFSM.input_threshold)
async def process_threshold(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['threshold'] = int(callback_query.data)
        start_date = data['start_date']
        end_date = data['end_date']
        threshold = data['threshold']

    DELTA_REPORT_DIR = 'delta_reports'
    api_key = os.getenv('API_TOKEN')
    myk_api_key = os.getenv('MYK_API_KEY')

    try:
        # Создание и загрузка отчета
        downloader = ReportDownloader(api_key, DELTA_REPORT_DIR)

        # Расчет диапазона дат
        start_date_dt = datetime.strptime(start_date, '%d.%m.%Y')
        end_date_dt = datetime.strptime(end_date, '%d.%m.%Y')
        today = datetime.now()

        # Вычисляем количество дней в исходном диапазоне
        delta_days = (end_date_dt - start_date_dt).days

        # Расширяем диапазон на delta_days дней назад
        extended_start_date_dt = start_date_dt - timedelta(days=delta_days + 1)

        # Сдвигаем весь расширенный диапазон на один день назад
        adjusted_start_date_dt = extended_start_date_dt - timedelta(days=1)
        adjusted_end_date_dt = end_date_dt - timedelta(days=1)

        # Проверка, если конечная дата больше или равна текущей дате, то сдвигаем её на один день назад
        if adjusted_end_date_dt >= today:
            adjusted_end_date_dt -= timedelta(days=1)

        adjusted_start_date = adjusted_start_date_dt.strftime('%Y-%m-%d')
        adjusted_end_date = adjusted_end_date_dt.strftime('%Y-%m-%d')

        print(f"Создание отчета с датами: {adjusted_start_date} - {adjusted_end_date}")
        report_id = downloader.create_report(adjusted_start_date, adjusted_end_date)

        # Проверка статуса отчета и скачивание данных
        if downloader.check_report_status(report_id):
            print("Отчет готов, скачивание данных...")
            extracted_folder = downloader.download_report(report_id)
            csv_file_path = downloader.find_csv_file(extracted_folder)
            print(f"CSV файл найден по пути: {csv_file_path}")
            excel_file_path = downloader.convert_csv_to_excel(csv_file_path)
            print(f"Excel файл сохранен по пути: {excel_file_path}")

            # Обработка отчета
            aggregator = ReportAggregator(file_path=excel_file_path, api_key=api_key, myk_key=myk_api_key, delta_threshold=threshold)
            output_file_path, missing_nmid_file_path = aggregator.run()
            print(f"Итоговый файл: {output_file_path}")
            print(f"Список отсутствующих артикулов: {missing_nmid_file_path}")

            await bot.send_document(
                chat_id=callback_query.from_user.id,
                document=open(output_file_path, 'rb'),
                caption="Итоговый отчет"
            )

            await bot.send_document(
                chat_id=callback_query.from_user.id,
                document=open(missing_nmid_file_path, 'rb'),
                caption="Список отсутствующих артикулов"
            )
        else:
            print("Отчет не был успешно создан или загружен.")

    except Exception as e:
        print(f"Ошибка: {e}")
        await bot.send_message(chat_id=callback_query.from_user.id, text=f"Произошла ошибка: {str(e)}")

    await state.finish()
    await callback_query.answer()


def run_bot():
    scheduler.start()
    executor.start_polling(dp, loop=asyncio.get_event_loop())


if __name__ == '__main__':
    dp.register_message_handler(on_start, commands=['start'])

    scheduler.add_job(send_notifications, 'cron', hour=9, minute=0)
    scheduler.add_job(send_notifications, 'cron', hour=14, minute=0)
    scheduler.add_job(send_notifications, 'cron', hour=17, minute=0)

    scheduler.add_job(send_free_whs, 'interval', minutes=3)
    scheduler.add_job(send_booking_info, 'interval', seconds=30)

    run_bot()
