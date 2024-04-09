import logging
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

    url = "https://seller-supply.wildberries.ru/ns/sm-supply/supply-manager/api/v1/supply/acceptanceCoefficientsReport"
    headers = {
        'Content-Type': 'application/json',
        'Cookie': '_wbauid=9110205211698128745; ___wbu=12ae082d-b28d-44c4-b9ac-493a84ce6307.1698128748; BasketUID=dd4dccdf3ec848f1949710a632e14fea; external-locale=ru; x-supplier-id-external=3117fcc2-af08-5e08-835d-8a036116acd0; wbx-validation-key=bead8ca0-c64d-4cf1-b194-064ea8a49f38; WILDAUTHNEW_V3=FB4C73FC3644B802F2858168DBD4F0AA5C0A9F635D887CE8ED6AAA4CD5BEC78BD9A4C10CE1026930E37161A16644043491ED4450A55EA58F39A6EFA16C38F59B8BDD721DC107F00AD24019EA33393D2C87EB4A17E40E5CD94231165AFCC805BB81CAD8D8B3DA8BAA9779F832F9F9882AF5773D23E4FD88692B59CEBCFB9333B4CA42F183CC9C482ABED2FB73319CCAAFDEAFDC640141826D0EBE1A457AA43F9A1DB5ADC8AA49DC3F192F657550EB3C9BA820AF6E31F19E882DF8DCFF3497157F3C8EC14FD98E62153838B0ECC77F192E3FB52433C705C046A63D02ABC1C91F4918F44B6201064B63039BD1B22DD422237C7184C147F07EE06EDB7DD174889793EEAA1508B9E20DDB11E7A1E51040E6838EB3B616838E40FE2E638B60614E9B4092DB7B14EC50075B10B017C4BF756FDFD5DBBA0E; device_id_guru=18e08cd3ada-41b0c8de0fc5a13f; client_ip_guru=5.167.249.195; _ym_uid=1709544651663368814; _ym_d=1709544651; front-wbguide=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6NTM1Mjg0MSwibmFtZSI6ItCU0LDQvdC40LsiLCJ5YW5kZXhfaWQiOm51bGwsImFjY2Vzc2VzIjpbeyJpZCI6MSwibmFtZSI6ImFydGljbGVzIiwiZGVzY3JpcHRpb24iOiLQodC-0LfQtNCw0L3QuNC1INGB0YLQsNGC0LXQuSJ9XSwiYWN0aXZlIjp0cnVlLCJzZXNzaW9uX2lkIjoiZjgzOWMwM2NjMzkwNGUyMjk0ODdhYjdmZWQ3OTI4MzMiLCJzaGFyZF9pZCI6IjEwIiwiZXhwIjoxNzQxMDgwNjUyfQ; adult-content-wbguide=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJTaG93QWR1bHQiOmZhbHNlLCJleHAiOjE3NDEwODA2NTJ9; WBTokenV3=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3MTI2Njg1ODksInZlcnNpb24iOjIsInVzZXIiOiI5MTkwMDQ4Iiwic2hhcmRfa2V5IjoiMSIsImNsaWVudF9pZCI6InNlbGxlci1wb3J0YWwiLCJzZXNzaW9uX2lkIjoiMjA2Yjg0NDNlZWYzNDE3ZGE3MGIyNTIwMDkxYWYxMmYiLCJ1c2VyX3JlZ2lzdHJhdGlvbl9kdCI6MTY2NTkwMzIzMSwidmFsaWRhdGlvbl9rZXkiOiJlZWM5MGYwNWYzNjcxYzQ3Y2E4OWMyYWVjMDFjMjg2ZGI1Mjk1OTBkNmY2ZWFkOTM0NDVmMzUxOGRmNDVlYmI4IiwicGhvbmUiOiJsa3ppUTUwM2hMOHZseW1DamtjQitRPT0ifQ.nC4zdhpzKxuV-L5ML5NlqL41JT3HaN-gYha2kYV7JkOBNKCKelrUKvPHrSvRnibzZRpeeg3Prr6ay63nTw18gtnOpLBcaae0iFtmlOBHAEaQufBvbgAh29feamHuoNRHUv4qWnJ9BDhJT8ojcIrCCt7To4OqNOr253bwfixD7IFRAsGhSnZc-9PG0UcxCaq1sJYdPX-waUCe3Rk0d2CwZv733Und14XJYfLhpLUlaeiXW7l-J_oox7cI1dsouKvRK7EN88uY8CSBAoiqIznOe3txDlH4XhWYHRkzekfKE0TNLtSoegw27RqANpUKilkRXPbnIBW-S1zScGRsgU9KcQ; cfidsw-wb=TKt5d8K2Lc99O2rIBkFOtsZHzrDPjzoioKytRiwOVUS9whJtJzbQa4xQJicaf9dMbYoY79zQmbWNU50KG3xFKaOUe9pRH86he+Q+ZQVV3eu5lzU7M/QMyKuW94T5MbHngcStUUfq+t9phBKANfS26EsB9mCk+72sIg8LeCKl; __zzatw-wb=MDA0dC0cTHtmcDhhDHEWTT17CT4VHThHKHIzd2UyPG4dX0thET9HFTZnXEpCNxVZcU4nfAsmMl4tYQ8rCB5UNV9OCCYbF31zKVIKDl1FPV8/cnsiD2k5IVt0FhNFWmFVaUAfQTY6flJkGBRIWRw2czljajUjfj1qTnsJXSVPDT1jQUVwMF5xaCFgThVQSlV/eyobEXd0JAg9DF1zM2llaXAvYCASJRFNRxhFZFtCNigVS3FPHHp2X30qQmYfZU1hJUZYUHwlFXtDPGMMcRVNfX0mNGd/ImUrOS4bNSIYNmdITT4mVBM8dWUQMzssZQgiD2k5I2Q1UT9BWltUODZnQRF1JgkINyxgcFcZURMaXHhHV3osGhN9cStVCg5eQENpZW0MLVJRUUtffw4OP2lOWUNdcEtxTih9CTE0Xn0cVhs5Y2o1I349ak57CV0mUAgSGXB0b3BacWUlXEwWH0tSVXwqTQ5/JCNSDQxcQ3IoLyktYQ8nfCNifCAZay8LVEMyZQg+QE05Mzk0ZnBXJ2BOWiFJW1V/KBwXeXEfQUtUI3Izd2Vpdx5WJRMWZw9HIk4=iB+rSA=='
    }
    payload = {
        "params": {
            "dateTo": date_to,
            "dateFrom": date_from
        },
        "jsonrpc": "2.0",
        "id": "json-rpc_16"
    }
    print('работаю')
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
        "Екатеринбург - Испытателей 14г", "Екатеринбург - Перспективный 12/2"
    ]

    if "result" in report:
        return [item for item in report["result"]["report"] if item.get("acceptanceType") == 6 and item.get('warehouseName') in special_warehouses]
    else:
        return []

print(send_request())