import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from celery_misc import celery_utils, utils, model_utils
from celery_misc.transactional_outbox import settings, enums, models

logger = logging.getLogger(__name__)


@shared_task(bind=True,
             max_retries=settings.SEND_EVENTS_MAX_RETRIES,
             retry_backoff=settings.SEND_EVENTS_RETRY_BACKOFF,
             retry_backoff_max=settings.SEND_EVENTS_RETRY_BACKOFF_MAX,
             retry_jitter=settings.SEND_EVENTS_RETRY_JITTER)
def send_events_only_ones(self, *args, **kwargs):
    """ Однократная отсылка созданных событий """
    return celery_utils.common_celery_task(self, _send_events, *args, **kwargs)


@shared_task(bind=True)
def send_events(self, *args, **kwargs):
    """ Периодическая отсылка не отправленных сообщений """
    return celery_utils.safety_celery_task(self, _send_events, *args, suppress_events_error=True, **kwargs)


@shared_task(bind=True)
def expiring_events(self, *args, **kwargs):
    """ Периодическая задача, которая помечает сообщения как устаревшие """
    return celery_utils.safety_celery_task(self, _expiring_events, *args, **kwargs)


@shared_task(bind=True)
def delete_events(self, *args, **kwargs):
    """ Периодическая задача, которая удаляет устаревшие сообщения """
    return celery_utils.safety_celery_task(self, _delete_events, *args, **kwargs)


def _send_events(_, event_ids: list[int] = None, suppress_events_error: bool | None = False,
                 batch_size: int | None = 50):
    """ Отправка уведомлений во внешнюю систему, например в kafka или rabbit """
    StrategyClass = utils.load_class(settings.SEND_EVENTS_STRATEGY)
    strategy = StrategyClass(batch_size=batch_size)
    error_messages = strategy.send_events(event_ids=event_ids)
    if not suppress_events_error and error_messages:
        error_ids = ','.join([str(e) for e in error_messages])
        raise Exception('Возникли ошибки при отправке сообщений с ID "%s".', error_ids)


def _expiring_events(_, expiration_delta_in_hours: int | None = 12):
    expiration_filter = ~Q(Q(status=enums.EventStatuses.SENT) | Q(status=enums.EventStatuses.EXPIRED))
    if expiration_delta_in_hours > 0:
        expiration_date = timezone.now() - timedelta(hours=expiration_delta_in_hours)
        expiration_filter &= Q(created_at__lt=expiration_date)

    def __expiring_queryset(qs, item_ids: list):
        count = qs.model.objects.filter(id__in=item_ids).update(status=enums.EventStatuses.EXPIRED)
        return count

    queryset = models.OutboxMessage.objects.filter(expiration_filter)
    model_utils.batch_processing(queryset, expiration_filter, __expiring_queryset)


def _delete_events(_, expiration_delta_in_hours: int | None = 24):
    delete_filter = Q()
    if expiration_delta_in_hours > 0:
        expiration_date = timezone.now() - timedelta(hours=expiration_delta_in_hours)
        delete_filter &= Q(created_at__lt=expiration_date)

    queryset = models.OutboxMessage.objects.filter(delete_filter)
    model_utils.batch_delete(queryset, delete_filter)
