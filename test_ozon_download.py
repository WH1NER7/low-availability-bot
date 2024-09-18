import os
from datetime import datetime

import requests
import time

from database import mark_ozon_report_as_processed, save_ozon_report_to_db, report_exists_in_db, \
    report_exists_in_db_by_filename, mark_ozon_realization_report_as_processed


# Функция для скачивания отчета по реализациям
def download_realization_report(report, headers):
    # Проверяем, существует ли отчет в базе данных по fileName
    file_name = report['fileName']

    print(f"Проверка на наличие отчета с fileName: {file_name}")
    if report_exists_in_db_by_filename(file_name):
        print(f"Отчет с fileName '{file_name}' уже существует в базе данных. Скачивание пропущено.")
        return

    report_id = report['id']
    report_type = "RealizationReportGeneralBilling"

    # Преобразуем дату в формат "DD-MM-YYYY"
    report_date_obj = datetime.strptime(report['date'], "%Y-%m-%dT%H:%M:%S")
    formatted_date = report_date_obj.strftime("%d-%m-%Y")

    # Генерируем новое имя файла на основе name, даты и id
    custom_filename = f"{report['name']}_{formatted_date}_{report_id}.xlsx"

    # Папка для сохранения файлов
    download_folder = "downloaded_reports"
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    file_path = os.path.join(download_folder, custom_filename)

    # URL для создания отчета
    post_url = "https://seller.ozon.ru/api/site/self-reports/api/reports/ask"

    # Тело запроса
    body = {
        "report_id": report_id,
        "report_type": report_type,
        "language": "ru",
        "filename": file_name
    }

    # Выполняем POST запрос
    response = requests.post(post_url, headers=headers, json=body)

    if response.status_code == 200:
        print(f"Запрос на создание отчета '{file_name}' успешен!")
    else:
        print(f"Ошибка при создании отчета: {response.status_code}, {response.text}")
        return

    # 2. GET запрос для проверки статуса отчета
    report_status_url = f"https://seller.ozon.ru/api/site/self-reports/api/reports/{report_id}/status"
    query_params = {
        "filename": file_name,
        "report_type": report_type,
        "language": "RU"
    }

    # Проверяем статус отчета с интервалом
    while True:
        status_response = requests.get(report_status_url, headers=headers, params=query_params)
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data.get('status') == 'Ready':
                print(f"Отчет '{file_name}' готов к скачиванию!")
                break
            else:
                print(f"Отчет '{file_name}' еще не готов. Ожидание...")
        else:
            print(f"Ошибка при проверке статуса: {status_response.status_code}, {status_response.text}")
            return

        # Ждем 5 секунд перед повторной проверкой
        time.sleep(5)

    # 3. GET запрос для скачивания отчета
    report_download_url = f"https://seller.ozon.ru/api/site/self-reports/api/reports/{report_id}/download"
    download_params = {
        "filename": file_name,
        "report_type": report_type,
        "language": "RU",
        "file_name": file_name
    }

    download_response = requests.get(report_download_url, headers=headers, params=download_params)

    if download_response.status_code == 200:
        # Сохраняем файл в папку downloaded_reports
        with open(file_path, 'wb') as file:
            file.write(download_response.content)
        print(f"Отчет '{custom_filename}' успешно скачан и сохранен в {download_folder}.")

        # Обновляем информацию в БД
        report['file_path'] = file_path  # Добавляем путь к файлу в отчет
        save_ozon_report_to_db(report)
        mark_ozon_realization_report_as_processed(report['key'])
    else:
        print(f"Ошибка при скачивании отчета: {download_response.status_code}, {download_response.text}")
