import os
import time
import uuid
import zipfile
import requests
import pandas as pd


class ReportDownloader:
    def __init__(self, api_key, delta_reports_dir):
        self.api_key = api_key
        self.delta_reports_dir = delta_reports_dir
        self.create_report_url = "https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads"
        self.check_report_url = "https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads"
        self.download_report_url = "https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads/file/{}"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    def generate_report_id(self):
        return str(uuid.uuid4())

    def create_report(self, start_date, end_date, brand_name="MissYourKiss"):
        report_id = self.generate_report_id()
        payload = {
            "id": report_id,
            "reportType": "DETAIL_HISTORY_REPORT",
            "userReportName": "Card report",
            "params": {
                "nmIDs": [],
                "subjectIDs": [],
                "brandNames": [brand_name],
                "tagIDs": [],
                "startDate": start_date,
                "endDate": end_date,
                "timezone": "Europe/Moscow",
                "aggregationLevel": "day",
                "skipDeletedNm": False
            }
        }
        response = requests.post(self.create_report_url, headers=self.headers, json=payload)
        if response.status_code == 200:
            print(f"Отчет {report_id} создан успешно.")
            return report_id
        else:
            raise Exception(f"Ошибка при создании отчета: {response.text}")

    def check_report_status(self, report_id):
        while True:
            time.sleep(1)
            response = requests.get(self.check_report_url, headers=self.headers)
            reports = response.json().get('data', [])

            report_status = None
            for report in reports:
                if report['id'] == report_id:
                    report_status = report['status']
                    break

            if report_status == "SUCCESS":
                print(f"Отчет {report_id} готов")
                return True
            else:
                print(f"Статус отчета {report_id}: {report_status}")
        return False

    def download_report(self, report_id):
        download_url = self.download_report_url.format(report_id)
        response = requests.get(download_url, headers=self.headers)

        zip_file_path = os.path.join(self.delta_reports_dir, f"{report_id}.zip")
        with open(zip_file_path, "wb") as report_file:
            report_file.write(response.content)

        print(f"Отчет сохранен как {zip_file_path}")

        extracted_folder = os.path.join(self.delta_reports_dir, f"{report_id}_extracted")
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_folder)

        print(f"Отчет извлечен в папку {extracted_folder}")
        return extracted_folder

    def find_csv_file(self, extracted_folder):
        for root, dirs, files in os.walk(extracted_folder):
            for file in files:
                if file.endswith('.csv'):
                    return os.path.join(root, file)
        return None

    def convert_csv_to_excel(self, csv_file_path):
        if csv_file_path is None:
            print("CSV файл не найден в распакованной директории.")
            return None
        else:
            df = pd.read_csv(csv_file_path)
            excel_file_path = csv_file_path.replace('.csv', '.xlsx')
            df.to_excel(excel_file_path, index=False)
            print(f"CSV файл конвертирован и сохранен как {excel_file_path}")
            return excel_file_path
