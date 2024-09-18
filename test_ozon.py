import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

from test_compensation_download_test import download_compensation_report
from test_ozon_download import download_realization_report


def fetch_realization_reports(headers, company_name):
    urls = {
        "realizationReports": "https://seller.ozon.ru/app/finances/documents?type=realizationReports",
        "compensationsAndOtherCharges": "https://seller.ozon.ru/app/finances/documents?type=compensationsAndOtherCharges"
    }

    today = datetime.today()
    first_day_of_current_month = datetime(today.year, today.month, 1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    control_date = last_day_of_previous_month.strftime('%Y-%m-%dT%H:%M:%S')

    print(f"[{company_name}] Контрольная дата (последний день предыдущего месяца): {control_date}")

    def process_url(url, report_type):
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            print(f"[{company_name}] Запрос успешен для {report_type}!")

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            script_tags = soup.find_all('script', attrs={'nonce': True})

            for script_tag in script_tags:
                if len(script_tag.attrs) == 1 and 'nonce' in script_tag.attrs:
                    if script_tag.string and 'window.__MODULE_STATE__=window.__MODULE_STATE__||{}' in script_tag.string:
                        script_content = script_tag.string.strip()
                        json_str = script_content.replace('(window.__MODULE_STATE__=window.__MODULE_STATE__||{})["finances"]=', '').rstrip(';')

                        try:
                            extracted_json = json.loads(json_str)
                            print(f"[{company_name}] Успешно преобразовано в JSON для {report_type}:")

                            if report_type == "Realization Reports":
                                realization_reports = extracted_json['financesModule']['documents']['realizationReportsModule']['realizationReports']
                                for report in realization_reports:
                                    report_date_str = report['date'].rstrip('Z')
                                    report_date = datetime.strptime(report_date_str, '%Y-%m-%dT%H:%M:%S')

                                    if report_date >= datetime.strptime(control_date, '%Y-%m-%dT%H:%M:%S'):
                                        filtered_report = {
                                            'id': report['id'],
                                            'date': report['date'],
                                            'fileName': report['fileName'],
                                            'key': report['key'],
                                            'name': report['name']
                                        }
                                        print(f"[{company_name}] Найден отчет: {filtered_report}")
                                        download_realization_report(filtered_report, headers)

                            elif report_type == "Compensations and Other Charges":
                                compensation_reports = extracted_json['financesModule']['documents']['compensationAndChargesModule']['compensationAndCharges']
                                for report in compensation_reports:
                                    report_date_str = report['date'].rstrip('Z')
                                    report_date = datetime.strptime(report_date_str, '%Y-%m-%dT%H:%M:%S')

                                    if report_date >= datetime.strptime(control_date, '%Y-%m-%dT%H:%M:%S'):
                                        filtered_report = {
                                            'id': report['id'],
                                            'date': report['date'],
                                            'fileName': report['fileName'],
                                            'key': report['key'],
                                            'name': report['name']
                                        }
                                        print(f"[{company_name}] Найден отчет: {filtered_report}")
                                        download_compensation_report(filtered_report, headers)

                        except json.JSONDecodeError as e:
                            print(f"[{company_name}] Ошибка при декодировании JSON для {report_type}: {e}")
                        break
            else:
                print(f"[{company_name}] Не удалось найти тег <script> с только атрибутом 'nonce' для {report_type}.")
        else:
            print(f"[{company_name}] Ошибка запроса для {report_type}: {response.status_code}")

    process_url(urls["realizationReports"], "Realization Reports")
    process_url(urls["compensationsAndOtherCharges"], "Compensations and Other Charges")

