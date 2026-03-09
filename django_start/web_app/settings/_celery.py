from celery.schedules import crontab
from envparse import env

from django_start.web_app.settings._redis import REDIS_CONNECTION_STRING

CELERY_BROKER_URL = REDIS_CONNECTION_STRING
CELERY_HIJACK_ROOT_LOGGER = False
CELERY_EAGER = env.bool('CELERY_EAGER', default=False)
VISIBILITY_TIMEOUT_IN_SEC = env.int('VISIBILITY_TIMEOUT_IN_SEC', default=3600)
BROKER_POOL_LIMIT = env.int('BROKER_POOL_LIMIT', default=10)
TASK_ACKS_LATE = env.bool('TASK_ACKS_LATE', default=False)
TASK_REJECT_ON_WORKER_LOST = env.bool('TASK_REJECT_ON_WORKER_LOST', default=False)
TASK_ACKS_ON_FAILURE = env.bool('TASK_ACKS_ON_FAILURE', default=True)
CELERY_CONCURRENCY = env.int('CELERY_CONCURRENCY', default=5)
WORKER_PREFETCH_MULTIPLIER = env.int('WORKER_PREFETCH_MULTIPLIER', default=4)
KEY_PREFIX = env.str('KEY_PREFIX', default='web_app0')
CELERY_BEAT_SCHEDULE = {
    'Зачистка лога выполненных задач': {
        'task': 'celery_misc.celery_monitoring.tasks.delete_running_log_task',
        'schedule': crontab(minute='*/20'),  # every 20 min
        'enabled': False,
    },
    'Ping': {
        'task': 'web_app.tasks.ping',
        'schedule': crontab(minute='*/20'),  # every 20 min
        'enabled': False,
    },
    'Бесконечное выполнение': {
        'task': 'web_app.tasks.inf_running',
        'schedule': crontab(minute='*/20'),  # every 20 min
        'enabled': False,
    },
    'Задача без контекста': {
        'task': 'web_app.tasks.not_bind',
        'schedule': crontab(minute='*/20'),  # every 20 min
        'enabled': False,
    }
}
