import base64
import os
import time
import zipfile

import requests
import datetime
from database import save_report, report_exists, mark_report_as_processed, get_document_name_by_service_name, \
    get_document_name_by_report_id
from pytz import timezone

from test_ozon import fetch_realization_reports

# Устанавливаем заголовки, если нужны (например, для cookie)
HEADERS_ACTS_MYK = {
    "Authorization": os.getenv("HEADERS_ACTS_MYK")
}

HEADERS_ACTS_BON = {
    "Authorization": os.getenv("HEADERS_ACTS_BON")
}

HEADERS_REPORTS_MYK = {
    "Cookie": os.getenv("HEADERS_REPORTS_MYK")
}

HEADERS_REPORTS_BNS = {
    "Cookie": os.getenv("HEADERS_REPORTS_BNS")
}

HEADERS_OZON_MYK = {
    'Cookie': os.getenv("HEADERS_OZON_MYK"),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 YaBrowser/24.7.0.0 Safari/537.36',
    "Accept-Language": "ru,en;q=0.9",
    "X-O3-Company-Id": "1043385"
}

HEADERS_OZON_BON = {
    'Cookie': os.getenv("HEADERS_OZON_BON"),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 YaBrowser/24.7.0.0 Safari/537.36',
    "Accept-Language": "ru,en;q=0.9",
    "X-O3-Company-Id": "1387502"
}

# API пути
DOCUMENTS_API_BASE = "https://documents-api.wildberries.ru/api/v1/documents/list"
REPORTS_API_BASE = "https://seller-services.wildberries.ru/ns/reports/sup-balance/api/v1/reports-weekly"

# Папка для хранения скачанных отчетов
DOWNLOAD_DIR = "downloaded_reports"


def save_base64_document(base64_data, file_name):
    """Сохранение документа из base64."""
    file_path = os.path.join("downloaded_reports", file_name)

    # Создаем папку, если она не существует
    if not os.path.exists("downloaded_reports"):
        os.makedirs("downloaded_reports")

    # Декодируем и сохраняем файл
    with open(file_path, 'wb') as file:
        file.write(base64.b64decode(base64_data))

    return file_path


def extract_zip(file_path, extract_name=None):
    """Распаковывает zip архив и возвращает пути к извлеченным файлам .xlsx."""
    extracted_files = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            extract_path = os.path.join(os.path.dirname(file_path), os.path.splitext(os.path.basename(file_path))[0])
            zip_ref.extractall(extract_path)

            # Переименовывание и сбор всех файлов .xlsx
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    if file.endswith('.xlsx'):
                        old_file_path = os.path.join(root, file)
                        new_file_name = extract_name if extract_name else file
                        new_file_path = os.path.join(root, new_file_name)

                        # Переименовываем файл
                        os.rename(old_file_path, new_file_path)
                        extracted_files.append(new_file_path)

            print(f"Файл {file_path} успешно распакован в {extract_path}")
    except zipfile.BadZipFile:
        print(f"Файл {file_path} не является корректным zip архивом.")

    return extracted_files


def download_document(service_name, extension, headers, document_name):
    """Скачивание документов через documents API."""
    download_url = "https://documents-api.wildberries.ru/api/v1/documents/download"
    params = {
        "serviceName": service_name,
        "extension": extension
    }

    response = requests.get(download_url, params=params, headers=headers)

    if response.status_code == 200:
        response_data = response.json().get('data', {})
        document_base64 = response_data.get('document')
        file_name = response_data.get('fileName')

        if not document_base64 or not file_name:
            print(f"Ошибка: не удалось получить документ для {service_name}")
            return []

        # Сохраняем файл из base64
        file_path = save_base64_document(document_base64, file_name)

        # Используем переданное имя документа для переименования
        if not document_name:
            document_name = file_name

        # Если файл является zip-архивом, распаковываем его и возвращаем пути к .xlsx файлам
        if file_name.endswith('.zip'):
            # Переименовываем извлеченные .xlsx файлы в соответствии с document_name
            return extract_zip(file_path, f"{document_name}.xlsx")

        # Переименовываем одиночный файл в соответствии с document_name
        new_file_path = os.path.join(os.path.dirname(file_path), f"{document_name}.xlsx")
        os.rename(file_path, new_file_path)
        return [new_file_path]  # Возвращаем путь к одиночному файлу с новым именем
    else:
        print(f"Ошибка при скачивании документа {service_name}: {response.status_code}")
        return []


def download_report(report_id, headers, base_url):
    """Скачивание отчетов через reports API."""
    download_url = f"{base_url}/{report_id}/details/archived-excel"
    response = requests.get(download_url, headers=headers)

    if response.status_code == 200:
        response_data = response.json()['data']
        report_base64 = response_data['file']
        file_name = response_data['name']

        # Сохраняем файл из base64
        file_path = save_base64_document(report_base64, file_name)

        # Если это zip-файл, распаковываем его
        if file_name.endswith('.zip'):
            return extract_zip(file_path, f"{file_name}.xlsx")
        return [file_path]  # Возвращаем путь к одиночному файлу
    else:
        print(f"Ошибка при скачивании отчета {report_id}: {response.status_code}")
        return []


def get_dates():
    """Возвращает начальную и конечную даты."""
    end_time = datetime.datetime.now(timezone('Europe/Moscow')).date()
    begin_time = end_time - datetime.timedelta(weeks=1)
    return begin_time, end_time


def fetch_documents(category, headers):
    """Получение документов через API WB для определенной категории."""
    begin_time, end_time = get_dates()
    params = {
        'locale': 'ru',
        'beginTime': begin_time.isoformat(),
        'endTime': end_time.isoformat(),
        'category': category
    }
    print(DOCUMENTS_API_BASE)
    response = requests.get(DOCUMENTS_API_BASE, params=params, headers=headers)
    if response.status_code == 200 and response.json().get('data', {}).get('documents', []) != None:
        return response.json().get('data', {}).get('documents', [])
    else:
        print(f"Ошибка при получении документов для категории {category}: {response.status_code}")
        return []


def process_and_download_documents(category, headers):
    """Процесс скачивания документов по категории и запись путей в БД."""
    documents = fetch_documents(category, headers)
    all_xlsx_files = []

    for doc in documents:
        service_name = doc['serviceName']
        extension = doc['extensions'][0] if doc['extensions'] else 'zip'
        document_name = doc['name']  # Получаем имя документа для переименования

        if not report_exists(service_name):  # Проверяем, существует ли отчет
            # Передаем document_name для использования в названии файла
            xlsx_files = download_document(service_name, extension, headers, document_name)
            time.sleep(5)
            all_xlsx_files.extend(xlsx_files)  # Добавляем все извлеченные файлы

            if xlsx_files:
                file_path = xlsx_files[0]  # Сохраняем путь к первому скачанному файлу
                save_report(service_name, doc, file_path)  # Сохраняем отчет в MongoDB с путём
                mark_report_as_processed(service_name, file_path)  # Отмечаем как обработанный с путём
                print(f"Документ {document_name} скачан и сохранен.")

    return all_xlsx_files



def fetch_reports(headers, base_url, report_type):
    """Получаем отчеты по API WB."""
    begin_time, end_time = get_dates()
    params = {
        'dateFrom': begin_time.isoformat(),
        'dateTo': end_time.isoformat(),
        'limit': 5,
        'skip': 0,
        'type': report_type  # Используем переданный тип отчета
    }
    print(base_url, ' fetch reps')
    response = requests.get(base_url, params=params, headers=headers)
    if response.status_code == 200:
        return response.json().get('data', {}).get('reports', [])
    else:
        print(f"Ошибка при получении отчетов: {response.status_code}")
        return []


def process_and_download_reports(header_report, base_url, report_type):
    """Процесс скачивания отчетов и запись путей в БД."""
    reports = fetch_reports(header_report, base_url, report_type)
    all_xlsx_files = []

    for report in reports:
        report_id = report['id']

        # Проверяем, был ли отчет уже обработан
        if report_exists(report_id):
            print(f"Отчет с ID: {report_id} уже обработан. Пропускаем его.")
            continue  # Пропускаем отчет, если он уже был обработан

        # Получаем имя отчета
        report_name = get_document_name_by_report_id(report_id)

        print(f"Скачивание отчета {report_name} с ID: {report_id}...")

        # Скачиваем отчет и распаковываем, если необходимо
        xlsx_files = download_report(report_id, header_report, base_url)

        # Если отчет успешно скачан, сохраняем его в базе данных
        if xlsx_files:
            file_path = xlsx_files[0]  # Сохраняем путь к первому скачанному файлу
            save_report(report_id, report, file_path)  # Сохраняем отчет в MongoDB с путём
            mark_report_as_processed(report_id, file_path)  # Отмечаем как обработанный с путём
            print(f"Отчет {report_name} успешно скачан.")
            all_xlsx_files.extend(xlsx_files)
        else:
            print(f"Не удалось скачать отчет {report_name} с ID: {report_id}.")

    return all_xlsx_files


def main_report_checker():
    print("Начинаем проверку отчетов и документов...")
    all_downloaded_xlsx = []

    # Обрабатываем категории документов
    categories = ['redeem-notification', 'actreturn', 'actutil']
    for headers in [HEADERS_ACTS_BON, HEADERS_ACTS_MYK]:
        for category in categories:
            time.sleep(1)
            xlsx_files = process_and_download_documents(category, headers)
            all_downloaded_xlsx.extend(xlsx_files)

    SUP_BALANCE_BASE_URL = "https://seller-services.wildberries.ru/ns/reports/sup-balance/api/v1/reports-weekly"
    SELLER_WB_BALANCE_BASE_URL = "https://seller-services.wildberries.ru/ns/reports/seller-wb-balance/api/v1/reports-weekly"

    report_configs = [
        (HEADERS_REPORTS_MYK, SUP_BALANCE_BASE_URL, 7),
        (HEADERS_REPORTS_BNS, SELLER_WB_BALANCE_BASE_URL, 6)
    ]

    # Обрабатываем отчеты
    for header_report, base_url, report_type in report_configs:
        report_xlsx_files = process_and_download_reports(header_report, base_url, report_type)
        all_downloaded_xlsx.extend(report_xlsx_files)

    # Добавляем проверку для реализационных отчетов двух компаний
    companies = [
        (HEADERS_OZON_MYK, "MissYourKiss"),
        # (HEADERS_OZON_BON, "Bonasita")
    ]

    for headers, company_name in companies:
        fetch_realization_reports(headers, company_name)

    print("Новые скачанные файлы .xlsx:")
    for file in all_downloaded_xlsx:
        print(file)

    return all_downloaded_xlsx


if __name__ == "__main__":
    main_report_checker()
