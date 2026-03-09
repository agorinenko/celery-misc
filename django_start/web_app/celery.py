import os

from celery import Celery
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')


app = Celery('web_app', broker=settings.CELERY_BROKER_URL)
app.config_from_object(settings, namespace='CELERY')
app.autodiscover_tasks()


transport_options = {
    'visibility_timeout': settings.VISIBILITY_TIMEOUT_IN_SEC,
    'global_keyprefix': settings.KEY_PREFIX
}

app.conf.update(
    accept_content=['json'],
    broker_transport_options=transport_options,
    broker_pool_limit=settings.BROKER_POOL_LIMIT,
    result_backend=settings.CELERY_BROKER_URL,
    result_backend_transport_options=transport_options,
    result_serializer='json',
    task_acks_late=settings.TASK_ACKS_LATE,
    task_always_eager=settings.CELERY_EAGER,
    task_serializer='json',
    task_reject_on_worker_lost=settings.TASK_REJECT_ON_WORKER_LOST,
    task_acks_on_failure_or_timeout=settings.TASK_ACKS_ON_FAILURE,
    worker_state_db=str(settings.BASE_DIR / 'celery-state'),
    worker_concurrency=settings.CELERY_CONCURRENCY,
    worker_prefetch_multiplier=settings.WORKER_PREFETCH_MULTIPLIER,
    broker_connection_retry_on_startup=True
)