# tasks.py
# from associated_advertisement_goods import collect_data
from celery_config import app

@app.task(name='tasks.add')
def add(x, y):
    return x + y


# @app.task
# def collect_data_task(company_api_key, api_key, start_date, end_date, authorizev3, cookie, user_agent):
#     print('111')
#     return collect_data(company_api_key, api_key, start_date, end_date, authorizev3, cookie, user_agent)
