import os
from datetime import datetime

import requests

from database import save_ozon_report_to_db, mark_ozon_report_as_processed, report_exists_in_db

# ID компании, которое всегда фиксировано
COMPANY_ID = 1043385

# Заголовки для запросов (нужно заменить на актуальные)



# Функция для скачивания отчета о компенсациях
def download_compensation_report(report, headers):
    # Проверяем, существует ли отчет в базе данных
    report_id = report['id']

    if report_exists_in_db(report_id):
        print(f"Отчет с ID {report_id} уже существует в базе данных. Скачивание пропущено.")
        return

    report_date = report['date']
    document_type = "DocumentMarketplaceSellerCompensationByTypeDoc"
    filename = report['fileName']

    # Преобразуем дату в формат "YYYY-MM-DD"
    report_date_obj = datetime.strptime(report_date, "%Y-%m-%dT%H:%M:%SZ")  # Преобразуем строку даты в объект
    formatted_date = report_date_obj.strftime("%Y-%m-%d")  # Форматируем объект в "YYYY-MM-DD"

    # Генерируем новое имя файла на основе name, даты и id
    custom_filename = f"{report['name']}_{formatted_date}_{report_id}.xlsx"

    # Папка для сохранения файлов
    download_folder = "downloaded_reports"
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    file_path = os.path.join(download_folder, custom_filename)

    # URL для скачивания отчета
    download_url = f"https://seller.ozon.ru/api/site/compensation/api/reports/{COMPANY_ID}/{report_id}/download"

    # Параметры запроса
    query_params = {
        "documentType": document_type,
        "language": "Russian"
    }

    # Выполняем GET запрос для скачивания отчета
    response = requests.get(download_url, headers=headers, params=query_params)

    if response.status_code == 200:
        # Сохраняем файл с новым именем
        with open(file_path, 'wb') as file:
            file.write(response.content)
        print(f"Отчет '{custom_filename}' успешно скачан и сохранен в {download_folder}.")

        # Обновляем статус processed и сохраняем file_path в БД
        report['file_path'] = file_path  # Добавляем путь к файлу в отчет
        save_ozon_report_to_db(report)
        mark_ozon_report_as_processed(report_id)
    else:
        print(f"Ошибка при скачивании отчета: {response.status_code}, {response.text}")
