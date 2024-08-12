from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery_app.task(name='celery_app.async_task_test')
def async_task_test(x, y):
    return x + y
