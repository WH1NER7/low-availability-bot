import logging
import os
from datetime import datetime, timedelta

import requests
import json


previous_report_file = "previous_report.json"
logging.basicConfig(filename='work_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')


def send_request():
    start_time = datetime.now()

    today = datetime.utcnow().date()

    # Получаем дату через 13 дней
    date_in_13_days = today + timedelta(days=13)

    # Преобразуем даты в нужный формат
    date_to = date_in_13_days.strftime("%Y-%m-%dT19:00:00.000Z")
    date_from = today.strftime("%Y-%m-%dT13:30:03.061Z")
    cookie = API_TOKEN = os.getenv('COOKIE')
    url = "https://seller-supply.wildberries.ru/ns/sm-supply/supply-manager/api/v1/supply/acceptanceCoefficientsReport"
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "PostmanRuntime/7.28.4",
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

    if response.status_code == 200:
        current_report = response.json()
        result = compare_reports(current_report)
        status = 'Ok'
    elif response.status_code == 403:
        result = 'Cookie устарели. Требуется обновить'
        status = 'Cookie dead'
    else:
        error_message = f"Неизвестная ошибка. Проверьте работоспособность запроса. Код ошибки: {response.status_code}."
        with open('error_log.txt', 'a') as f:
            f.write(f"{error_message}\n")

        status = 'Ошибочка'
        result = error_message

    end_time = datetime.now()  # Записываем время завершения выполнения функции
    execution_time = end_time - start_time  # Вычисляем время выполнения функции
    logging.info(f"Время выполнения: {execution_time.total_seconds()} сек. Статус: {status}")

    return result


def compare_reports(current_report):
    result_text = ""
    previous_report = load_previous_report()
    if previous_report:
        current_acceptance = filter_acceptance(current_report)
        previous_acceptance = filter_acceptance(previous_report)

        for current_item in current_acceptance:
            current_warehouse_id = current_item["warehouseID"]
            current_date = current_item["date"]
            date_object = datetime.strptime(current_date, "%Y-%m-%dT%H:%M:%SZ")

            # Форматирование объекта datetime в требуемый формат "день.месяц.год"
            formatted_date = date_object.strftime("%d.%m.%Y")
            current_coefficient = current_item["coefficient"]

            for previous_item in previous_acceptance:
                if current_item["warehouseID"] == previous_item["warehouseID"] and \
                        current_item["date"] == previous_item["date"]:
                    previous_coefficient = previous_item["coefficient"]
                    if previous_coefficient != 0 and current_coefficient == 0:
                        result_text += "Обнаружено изменение:\n"
                        result_text += f"Дата: {formatted_date}\n"
                        result_text += f"ID Склада: {current_warehouse_id}\n"
                        result_text += f"Название склада: {current_item['warehouseName']}\n"
                        result_text += f"Предыдущий коэф.: {previous_coefficient}\n"
                        result_text += f"Текущий коэф.: {current_coefficient}\n"
                        result_text += "------------------------\n"

    save_current_report(current_report)
    return result_text


def load_previous_report():
    try:
        with open(previous_report_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return None


def save_current_report(current_report):
    with open(previous_report_file, 'w') as file:
        json.dump(current_report, file)


def filter_acceptance(report):
    special_warehouses = [
        "Коледино", "Новосибирск", "Хабаровск", "Подольск",
        "Казань", "Электросталь", "Астана", "Белые столбы",
        "Тула", "Пушкино", "Невинномысск", "Алматы Атакент",
        "Санкт-Петербург (Уткина Заводь)", "Краснодар (Тихорецкая)",
        "Екатеринбург - Испытателей 14г", "Екатеринбург - Перспективный 12/2", "Подольск 4"
    ]

    if "result" in report:
        return [item for item in report["result"]["report"] if item.get("acceptanceType") == 6 and item.get('warehouseName') in special_warehouses]
    else:
        return []

