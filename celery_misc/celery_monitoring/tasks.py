from celery import shared_task

from celery_misc.celery_monitoring import monitoring_utils

from celery_misc import celery_utils


@shared_task(bind=True)
def delete_running_log_task(self, *args, **kwargs):
    """ Зачистка лога выполненных задач за прошедший период """
    return celery_utils.safety_celery_task(self, monitoring_utils.delete_tasks_log, *args, **kwargs)
