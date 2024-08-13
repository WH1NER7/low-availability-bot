from celery import Celery

from associated_advertisement_goods import collect_data

celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


@celery_app.task(name='celery_app.async_task_test')
def async_task_test(x, y):
    return x + y


@celery_app.task(name='celery_app.collect_data_task')
def collect_data_task(company_api_key, api_key, start_date, end_date, authorizev3, cookie, user_agent):
    return collect_data(company_api_key, api_key, start_date, end_date, authorizev3, cookie, user_agent)