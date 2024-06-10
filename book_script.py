import os

import requests
from datetime import datetime, timedelta
from pymongo import MongoClient

from book_warehouse import process_supply

# Настройки для подключения к MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client.low_limits_bot
collection = db.book_tasks

cookie = API_TOKEN = os.getenv('COOKIE')

user_ids_whs = [615742233, 1080039077, 5498524004, 6699748340, 6365718854]
error_notify_user_id = 615742233


def get_acceptance_coefficients():
    today = datetime.utcnow().date()
    date_in_13_days = today + timedelta(days=13)
    date_to = date_in_13_days.strftime("%Y-%m-%dT19:00:00.000Z")
    date_from = today.strftime("%Y-%m-%dT13:30:03.061Z")

    url = "https://seller-supply.wildberries.ru/ns/sm-supply/supply-manager/api/v1/supply/acceptanceCoefficientsReport"
    headers = {
        'Content-Type': 'application/json',
        'Cookie': cookie
    }
    payload = {
        "params": {
            "dateTo": date_to,
            "dateFrom": date_from
        },
        "jsonrpc": "2.0",
        "id": "json-rpc_16"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def get_tasks_from_mongo():
    tasks = list(collection.find({"status": "В процессе"}))
    return tasks


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").date()
    except ValueError:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").date()


def check_warehouses(tasks, report):
    matched_tasks = []
    for task in tasks:
        warehouse_id = task['warehouse_id']
        file_name = task['file_name']
        start_date = task['start_date']
        end_date = task.get('end_date', start_date)

        if isinstance(start_date, dict):
            start_date = datetime.strptime(start_date['$date'], "%Y-%m-%dT%H:%M:%S.%fZ").date()
        else:
            start_date = start_date.date()

        if isinstance(end_date, dict):
            end_date = datetime.strptime(end_date['$date'], "%Y-%m-%dT%H:%M:%S.%fZ").date()
        else:
            end_date = end_date.date()

        for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
            for entry in report['result']['report']:
                entry_warehouse_id = entry['warehouseID']
                entry_date = parse_date(entry['date'])
                acceptance_type = entry['acceptanceType']
                coefficient = entry['coefficient']

                if (entry_warehouse_id == warehouse_id and
                        acceptance_type == 6 and
                        coefficient == 0 and
                        single_date == entry_date):
                    task_with_date = {
                        "_id": task['_id'],
                        "date": single_date.strftime("%Y-%m-%dT00:00:00Z"),
                        "warehouse_id": warehouse_id,
                        "file_name": file_name
                    }
                    matched_tasks.append(task_with_date)
                    break
            else:
                continue
            break
    return matched_tasks


def update_task_status(collection):
    today = datetime.utcnow().date()
    tasks = list(collection.find({"status": "В процессе"}))
    for task in tasks:
        end_date = task.get('end_date')
        if isinstance(end_date, dict):
            end_date = datetime.strptime(end_date['$date'], "%Y-%m-%dT%H:%M:%S.%fZ").date()
        else:
            end_date = end_date.date()

        if end_date < today:
            collection.update_one({"_id": task['_id']}, {"$set": {"status": "Провалено"}})


def book_wh():
    successful_bookings = []
    errors = []

    # Настройки для подключения к MongoDB
    with MongoClient("mongodb://localhost:27017/") as client:
        db = client.low_limits_bot
        collection = db.book_tasks

        try:
            report = get_acceptance_coefficients()
            update_task_status(collection)
            tasks = get_tasks_from_mongo()
            matched_tasks = check_warehouses(tasks, report)

            for task in matched_tasks:
                try:
                    supply_status, supply_id = process_supply(task.get('date'), task.get('warehouse_id'),
                                                              task.get('file_name'), cookie)
                    if supply_status:
                        task_details = collection.find_one({"_id": task['_id']})
                        start_date = task_details['start_date']
                        if isinstance(start_date, dict):
                            start_date = start_date['$date']
                        end_date = task_details['end_date']
                        if isinstance(end_date, dict):
                            end_date = end_date['$date']
                        warehouse_name = task_details['warehouse_name']

                        date_range = start_date
                        if start_date != end_date:
                            date_range = f"{start_date} - {end_date}"

                        successful_booking = {
                            "supply_id": supply_id,
                            "date_range": date_range,
                            "warehouse_name": warehouse_name,
                            "user_ids": user_ids_whs
                        }
                        successful_bookings.append(successful_booking)

                        collection.update_one(
                            {"_id": task['_id']},
                            {"$set": {"status": "Успешно завершена", "supply_id": supply_id}}
                        )
                        print(f"Successfully booked supply with ID: {supply_id}")
                    else:
                        print(f"Booking failed for task: {task}")
                except Exception as e:
                    error_message = f"Booking failed for task {task}: {e}"
                    errors.append(error_message)
                    print(error_message)

        except Exception as e:
            errors.append(f"Failed to complete booking process: {e}")
            print(f"Failed to complete booking process: {e}")

    return successful_bookings, errors
