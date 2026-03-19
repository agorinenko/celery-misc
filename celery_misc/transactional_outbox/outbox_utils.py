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
    def __init__(self, event_type: str, strategy: str | None = None):
        """ Создание события для отправки """
        self.event_type = event_type
        self.payload = None
        self.idempotency_key = None
        self.instance = None
        self.event_ids = None
        self.strategy = strategy
        self.meta_data = None

        self._transaction = None

    def __enter__(self):
        self._transaction = transaction.atomic()
        self._transaction.__enter__()
        self._is_in_transaction = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                if not self.instance or not self.payload:
                    raise ValueError(
                        'Необходимо вызвать функцию send(instance, payload) внутри контекстного менеджера.')
                self._create_outbox_message()

            if self._transaction:
                self._transaction.__exit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            if self._transaction:
                self._transaction.__exit__(type(e), e, e.__traceback__)
            raise
        finally:
            self._transaction = None

    def send(self, instance: T,
             payload: dict | list[dict],
             idempotency_key: str | list[str] | None = None,
             meta_data: dict | list[dict] | None = None):
        if self._transaction is None:
            raise RuntimeError(
                'Метод send должен вызываться внутри контекстного менеджера OutboxEvent.'
            )

        self.instance = instance
        if not payload:
            raise ValueError('Параметр payload пуст или не указан.')

        if idempotency_key is None:
            if not isinstance(payload, list):
                self.idempotency_key = [str(uuid6.uuid7())]
            else:
                self.idempotency_key = [str(uuid6.uuid7()) for i in range(len(payload))]
        elif not isinstance(idempotency_key, list):
            self.idempotency_key = [idempotency_key]
        else:
            self.idempotency_key = idempotency_key

        meta_data_len = 0
        if meta_data:
            if not isinstance(meta_data, list):
                self.meta_data = [meta_data]
            else:
                self.meta_data = meta_data

            meta_data_len = len(self.meta_data)

        if not isinstance(payload, list):
            self.payload = [self._serialize_event(payload)]
        else:
            self.payload = [self._serialize_event(i) for i in payload]

        if len(self.payload) != len(self.idempotency_key):
            raise ValueError('Размерности параметров idempotency_key и payload не совпадают.')

        i = 0
        for event_payload, idempotency_key in zip(self.payload, self.idempotency_key, strict=True):
            event_payload['idempotency_key'] = idempotency_key
            if i < meta_data_len:
                event_payload['meta_data'] = self.meta_data[i]
            i += 1

    def _create_outbox_message(self):
        if len(self.payload) == 1:
            message = models.OutboxMessage.objects.create(**self.payload[0])
            self.event_ids = [message.id]
        else:
            objs = [models.OutboxMessage(**payload) for payload in self.payload]
            db_objs = models.OutboxMessage.objects.bulk_create(objs)
            self.event_ids = [msg.id for msg in db_objs]

        if self.event_ids:
            tasks.send_events_only_ones.apply_async(kwargs={'event_ids': self.event_ids})

    def _serialize_event(self, event_payload: dict) -> dict:
        aggregate_type = str(type(self.instance).__name__)
        aggregate_id = self.instance.id
        return {
            'aggregate_type': aggregate_type,
            'aggregate_id': aggregate_id,
            'event_type': self.event_type,
            'payload': event_payload,
            'strategy': self.strategy
        }
