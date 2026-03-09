import logging
import sys
import time

from celery_misc import celery_utils, errors
from celery_misc.celery_monitoring import monitoring_utils
from django_start.web_app.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True)
def ping(self, *args, **kwargs):
    """ Ping celery """
    return celery_utils.common_celery_task(self, _ping, *args, **kwargs)


@app.task(
    bind=True,
    max_retries=3,  # Максимальное количество повторных попыток
    default_retry_delay=1,  # Задержка между попытками в секундах
    retry_backoff=False,  # Экспоненциальное увеличение задержки
    retry_backoff_max=1,  # Максимальная задержка при экспоненциальном росте
    retry_jitter=False  # Добавляет случайность к задержке
)
def error_task(self, *args, **kwargs):
    """ Error celery """
    return celery_utils.common_celery_task(self, _error_task, *args, **kwargs)


@app.task(bind=True)
def long_running(self, *args, **kwargs):
    """ Long-running task """
    return celery_utils.common_celery_task(self, _long_running, *args, **kwargs)


@app.task(bind=True)
def inf_running(self, *args, **kwargs):
    """ Long-running task """
    return celery_utils.common_celery_task(self, _inf_running, *args, **kwargs)


@app.task(bind=False)
def not_bind():
    """ Задача без контекста """
    return celery_utils.safety_celery_task(_not_bind)

def _not_bind():
    print('1')

def _ping(*args, timeout: float | None = 0.0, **kwargs):
    if timeout > 0:
        time.sleep(timeout)
    return 'pong'


def _error_task(*args, **kwargs):
    raise Exception('Raise error.')


def _long_running(task, *args, **kwargs):
    for _ in range(sys.maxsize):
        instance = monitoring_utils.find_task(task)
        if instance.is_revoked:
            raise errors.SoftStop('Задача отозвана')
        else:
            instance.revoke_task()
        time.sleep(0.1)


def _inf_running(task, *args, **kwargs):
    for _ in range(sys.maxsize):
        # return
        instance = monitoring_utils.find_task(task)
        instance.update_duration()
        if instance.is_revoked:
            raise errors.SoftStop('Задача отозвана')
        time.sleep(1)
