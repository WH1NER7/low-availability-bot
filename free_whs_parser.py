from datetime import datetime, timedelta

import requests
import json


previous_report_file = "previous_report.json"


def send_request():
    today = datetime.utcnow().date()

    # Получаем дату через 13 дней
    date_in_13_days = today + timedelta(days=13)

    # Преобразуем даты в нужный формат
    date_to = date_in_13_days.strftime("%Y-%m-%dT19:00:00.000Z")
    date_from = today.strftime("%Y-%m-%dT13:30:03.061Z")

    url = "https://seller-supply.wildberries.ru/ns/sm-supply/supply-manager/api/v1/supply/acceptanceCoefficientsReport"
    headers = {
        'Content-Type': 'application/json',
        'Cookie': '_wbauid=9110205211698128745; ___wbu=12ae082d-b28d-44c4-b9ac-493a84ce6307.1698128748; BasketUID=dd4dccdf3ec848f1949710a632e14fea; external-locale=ru; x-supplier-id-external=3117fcc2-af08-5e08-835d-8a036116acd0; wbx-validation-key=bead8ca0-c64d-4cf1-b194-064ea8a49f38; __zzatw-wb=MDA0dC0cTHtmcDhhDHEWTT17CT4VHThHKHIzd2UuPGciX0xhITVRP0FaW1Q4NmdBEXUmCQg3LGBwVxlRExpceEdXeiwZE3dtJ1IKEGA/QmllbQwtUlFRS19/Dg4/aU5ZQ11wS3E6EmBWGB5CWgtMeFtLKRZHGzJhXkZpdRVgRzx3ClMuDGh7bERzYG0hDhEIHkohIjQXJWF/JAo+el9vG3siXyoIJGM1Xz9EaVhTMCpYQXt1J3Z+KmUzPGwdYUdbI0ZYUn4nGw1pN2wXPHVlLwkxLGJ5MVIvE0tsGA==NBSY5Q==; WILDAUTHNEW_V3=FB4C73FC3644B802F2858168DBD4F0AA5C0A9F635D887CE8ED6AAA4CD5BEC78BD9A4C10CE1026930E37161A16644043491ED4450A55EA58F39A6EFA16C38F59B8BDD721DC107F00AD24019EA33393D2C87EB4A17E40E5CD94231165AFCC805BB81CAD8D8B3DA8BAA9779F832F9F9882AF5773D23E4FD88692B59CEBCFB9333B4CA42F183CC9C482ABED2FB73319CCAAFDEAFDC640141826D0EBE1A457AA43F9A1DB5ADC8AA49DC3F192F657550EB3C9BA820AF6E31F19E882DF8DCFF3497157F3C8EC14FD98E62153838B0ECC77F192E3FB52433C705C046A63D02ABC1C91F4918F44B6201064B63039BD1B22DD422237C7184C147F07EE06EDB7DD174889793EEAA1508B9E20DDB11E7A1E51040E6838EB3B616838E40FE2E638B60614E9B4092DB7B14EC50075B10B017C4BF756FDFD5DBBA0E; device_id_guru=18e08cd3ada-41b0c8de0fc5a13f; client_ip_guru=5.167.249.195; _ym_uid=1709544651663368814; _ym_d=1709544651; front-wbguide=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6NTM1Mjg0MSwibmFtZSI6ItCU0LDQvdC40LsiLCJ5YW5kZXhfaWQiOm51bGwsImFjY2Vzc2VzIjpbeyJpZCI6MSwibmFtZSI6ImFydGljbGVzIiwiZGVzY3JpcHRpb24iOiLQodC-0LfQtNCw0L3QuNC1INGB0YLQsNGC0LXQuSJ9XSwiYWN0aXZlIjp0cnVlLCJzZXNzaW9uX2lkIjoiZjgzOWMwM2NjMzkwNGUyMjk0ODdhYjdmZWQ3OTI4MzMiLCJzaGFyZF9pZCI6IjEwIiwiZXhwIjoxNzQxMDgwNjUyfQ; adult-content-wbguide=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJTaG93QWR1bHQiOmZhbHNlLCJleHAiOjE3NDEwODA2NTJ9; WBTokenV3=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3MTA3NDgzMjMsInZlcnNpb24iOjIsInVzZXIiOiI1MTI1MDU4MiIsInNoYXJkX2tleSI6IjEwIiwiY2xpZW50X2lkIjoic2VsbGVyLXBvcnRhbCIsInNlc3Npb25faWQiOiJiYjQ0MjI2Yzk4MDc0YzcwOTEzZTFjNTVkNzIwMzc5NCIsInVzZXJfcmVnaXN0cmF0aW9uX2R0IjoxNjc3Nzc1MzY4LCJ2YWxpZGF0aW9uX2tleSI6ImVlYzkwZjA1ZjM2NzFjNDdjYTg5YzJhZWMwMWMyODZkYjUyOTU5MGQ2ZjZlYWQ5MzQ0NWYzNTE4ZGY0NWViYjgiLCJwaG9uZSI6ImFRS0dwUG51cEZrTnFXKzdvKy9tOVE9PSJ9.m3aDzynOqp5Oy2G3q4IpdkG5LSzl4v8-N6Wo8rwvUwzTiwB7P2s5fD3nToVxCBqfrPmbnYXdKlldLQ6d7--7FXU-DbHM3FZBN-_ZjGe2TCgGOK9-LSTTBs6Up8Be60ZrwT8A6uoKSXh-1AtYYRdNbzCrjF06AL9w6JqstkfbwCp6peoYgA5E39SeBl3STaVOsMOG9pJmC5BDGCb2GaC5pI3Ri3Ei1Y42Yy-nM2Qulx7Py0zeAO_T3favM0GNsoDIzjO_3NZeOcWyiYtAnlszXNclz2nvNWNooV4X2ImR9yvqu3CglS3ZXkMzSXev_XfU-nbVRf73U8a7s5lxBZi-pQ; cfidsw-wb=sbLFbn7UfCko9/cUIcLtnd86na1ihSKwM7qsuf/kLLkxx6obEkSXDDXd2UiRP/0IhgZmh8aAWQbHRqix5u8MiLQ8sjHsP5x1+ViSaRdiwG2ulzXQDcTFkLnLWXz42XLj/YE1BPTKVO5/68RDKfZm7z67unEVc10PDkDqXzOO'
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
    print(response.status_code)

    if response.status_code == 200:
        current_report = response.json()
        return compare_reports(current_report)
    elif response.status_code == 403:
        return 'Cookie устарели. Требуется обновить'
    else:
        error_message = f"Неизвестная ошибка. Проверьте работоспособность запроса. Код ошибки: {response.status_code}."
        with open('error_log.txt', 'a') as f:
            f.write(f"{error_message}\n")
        return error_message


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
                        result_text += f"Тип: {current_item['acceptanceType']}\n"
                        result_text += f"Предыдущий коэф.: {previous_coefficient}\n"
                        result_text += f"Текущий коэф.: {current_coefficient}\n"
                        result_text += "------------------------\n"
    print(result_text)
    save_current_report(current_report)
    return result_text


def load_previous_report():
    try:
        with open(previous_report_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return None


def save_current_report(current_report):
    with open(previous_report_file, 'w', encoding='utf-8') as file:
        json.dump(current_report, file, ensure_ascii=False)
    print('Saved')


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
