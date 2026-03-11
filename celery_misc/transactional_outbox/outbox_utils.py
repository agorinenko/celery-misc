from typing import TypeVar

import uuid6
from django.db import transaction
from django.db.models import Model

from celery_misc.transactional_outbox import models, tasks, enums

T = TypeVar('T', bound=Model)


def resend_events(event_ids: list[int]):
    """ Повторная отправка сообщений """
    if not event_ids:
        raise ValueError('Event_ids is none or empty.')

    models.OutboxMessage.objects.filter(id__in=event_ids).update(status=enums.EventStatuses.PENDING, sent_at=None)
    tasks.send_events_only_ones.apply_async(kwargs={'event_ids': event_ids})


class OutboxEvent:
    def __init__(self, event_type: str):
        """ Создание события для отправки """
        self.event_type = event_type
        self.payload = None
        self.idempotency_key = None
        self.instance = None
        self.message_id = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if not self.instance or not self.payload:
                raise ValueError('Необходимо вызвать функцию send(instance, payload) внутри контекстного менеджера.')
            self._create_outbox_message()
            return True
        return False

    def send(self, instance: T, payload: dict, idempotency_key: str | None = None):
        self.instance = instance
        self.payload = payload
        self.idempotency_key = idempotency_key

    def _create_outbox_message(self):
        with transaction.atomic():
            aggregate_type = str(type(self.instance).__name__)
            aggregate_id = self.instance.id
            message_kwargs = {
                'aggregate_type': aggregate_type,
                'aggregate_id': aggregate_id,
                'event_type': self.event_type,
                'payload': self.payload
            }

            if self.idempotency_key:
                message, created = models.OutboxMessage.objects.get_or_create(idempotency_key=self.idempotency_key,
                                                                              **message_kwargs)
            else:
                message_kwargs['idempotency_key'] = str(uuid6.uuid7())
                message = models.OutboxMessage.objects.create(**message_kwargs)
                created = True

        if created:
            tasks.send_events_only_ones.apply_async(kwargs={'event_ids': [message.id]})

        self.message_id = message.id
