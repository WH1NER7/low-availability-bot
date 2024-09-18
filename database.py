from pymongo import MongoClient
from datetime import datetime

# Конфигурация MongoDB
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "wb_reports"
COLLECTION_NAME = "reports"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
reports_collection = db[COLLECTION_NAME]


def report_exists_in_db(report_id):
    """Проверяем, существует ли отчет с данным id в базе данных."""
    return reports_collection.find_one({"id": report_id}) is not None


# Функция для проверки существования отчета по fileName
def report_exists_in_db_by_filename(file_name):
    """Проверяем, существует ли отчет с данным fileName в базе данных."""
    report = reports_collection.find_one({"fileName": file_name})

    if report:
        print(f"Отчет с fileName '{file_name}' найден в базе данных: {report}")
        return True
    else:
        print(f"Отчет с fileName '{file_name}' НЕ найден в базе данных.")
        return False


def save_ozon_report_to_db(report):
    """Сохраняем информацию об отчёте в базе данных."""
    report_record = {
        "id": report['id'],
        "date": report['date'],
        "fileName": report['fileName'],
        "key": report['key'],
        "name": report['name'],
        "file_path": report.get('file_path', ""),  # Добавляем путь к файлу
        "processed": False,
        "sent": False
    }

    print(f"Сохраняем отчет с fileName '{report['fileName']}' в базу данных")

    # Обновляем или создаем запись по fileName
    result = reports_collection.update_one(
        {"fileName": report['fileName']},  # Условие для обновления по fileName
        {"$set": report_record},
        upsert=True  # Создаем запись, если её нет
    )

    print(f"Результат сохранения: {result.matched_count} совпадений, {result.modified_count} обновлений")


# Функция для обновления поля processed после успешной загрузки
def mark_ozon_report_as_processed(report_id):
    """Обновляем статус processed на True."""
    reports_collection.update_one(
        {"id": report_id},  # Находим отчет по id
        {"$set": {"processed": True}}  # Обновляем processed на True
    )


def mark_ozon_realization_report_as_processed(key):
    """Обновляем статус processed на True."""
    reports_collection.update_one(
        {"key": key},  # Находим отчет по id
        {"$set": {"processed": True}}  # Обновляем processed на True
    )


def save_report(report_id, report_data, file_path=None):
    """Сохраняем информацию о новом отчёте в базе данных."""
    report_record = {
        "report_id": report_id,
        "data": report_data,
        "processed": False,
        "sent": False
    }

    if file_path:
        report_record["file_path"] = file_path  # Добавляем путь к скачанному файлу

    reports_collection.update_one(
        {"report_id": report_id},
        {"$set": report_record},
        upsert=True  # Создаём запись, если её нет
    )


def mark_report_as_processed(report_id, file_path=None):
    """Обновляем статус отчёта как обработанный и добавляем путь к файлу."""
    update_fields = {"processed": True}

    if file_path:
        update_fields["file_path"] = file_path  # Обновляем путь к файлу, если есть

    reports_collection.update_one(
        {"report_id": report_id},
        {"$set": update_fields}
    )


def report_exists(report_id):
    """Проверка существования отчета."""
    return reports_collection.count_documents({"report_id": report_id, "processed": True}) > 0


def get_document_name_by_service_name(service_name):
    """Получение названия документа по его serviceName."""
    document = reports_collection.find_one({"serviceName": service_name})

    if document:
        return document.get("name", f"Документ {service_name}")
    return f"Документ {service_name}"


def get_unsent_reports():
    """
    Возвращает все отчеты, у которых статус 'sent' = False и 'status' = 'downloaded'.
    """
    return list(reports_collection.find({"processed": True, "sent": False}))


def mark_report_as_sent(report_id):
    """
    Обновляет статус отчета на 'sent = True' после отправки.
    """
    reports_collection.update_one(
        {"file_path": report_id},
        {"$set": {"sent": True}}
    )
    print(f"Отчет с ID {report_id} помечен как sent.")


def get_document_name_by_report_id(report_id):
    """Получение названия документа по его report_id."""
    document = reports_collection.find_one({"report_id": report_id})

    if document:
        return document.get("name", f"Документ {report_id}")
    return f"Документ {report_id}"
