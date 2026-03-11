from django.db import models


class EventStatuses(models.TextChoices):
    """ Статусы задач Celery """
    PENDING = 'pending', 'Ожидает обработки'
    SENT = 'sent', 'Отправлено'
    EXPIRED = 'expired', 'Устарело'
    FAILED = 'failed', 'Ошибка отправки'
