from datetime import timedelta
from unittest.mock import Mock

import pytest
import uuid6
from django.utils import timezone

from celery_misc.transactional_outbox import outbox_utils, models, enums, tasks

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('strategy', [
    'celery_misc.transactional_outbox.strategies.DummyCheckStatusStrategy',
    'celery_misc.transactional_outbox.strategies.DummyBlockBatchStrategy',
])
def test_send_events(mocker, strategy):
    """ Создание и отправка события """
    mocker.patch('celery_misc.transactional_outbox.settings.SEND_EVENTS_STRATEGY', strategy)
    aggregate_id = 123
    event_type = 'order.created'
    payload = {'total': 100}
    idempotency_key = 'test1234'
    with outbox_utils.OutboxEvent(event_type) as outbox_guard:
        # Здесь instance будет правильно типизирован как Order
        order = Mock()
        order.id = aggregate_id

        outbox_guard.send(order, payload, idempotency_key=idempotency_key)

    db_message = models.OutboxMessage.objects.filter(id=outbox_guard.message_id).first()
    assert db_message
    assert db_message.idempotency_key == idempotency_key
    assert db_message.aggregate_type == 'Mock'
    assert db_message.aggregate_id == str(aggregate_id)
    assert db_message.event_type == event_type
    assert db_message.payload == payload

    assert db_message.status == enums.EventStatuses.SENT
    assert db_message.created_at is not None
    assert db_message.sent_at is not None
    assert db_message.error is None


@pytest.mark.parametrize('strategy', [
    'celery_misc.transactional_outbox.strategies.DummyCheckStatusStrategy',
    'celery_misc.transactional_outbox.strategies.DummyBlockBatchStrategy',
])
def test_send_events__with_error(mocker, strategy):
    """ Создание и обработка ошибки отправки события """
    mocker.patch('celery_misc.transactional_outbox.settings.SEND_EVENTS_STRATEGY', strategy)

    publish_message_mocker = mocker.patch(f'{strategy}.publish_message')
    error = 'Error message!'
    publish_message_mocker.side_effect = Exception(error)
    aggregate_id = 123
    event_type = 'order.created'
    payload = {'total': 100}
    idempotency_key = 'test1234'
    with outbox_utils.OutboxEvent(event_type) as outbox_guard:
        # Здесь instance будет правильно типизирован как Order
        order = Mock()
        order.id = aggregate_id

        outbox_guard.send(order, payload, idempotency_key=idempotency_key)

    db_message = models.OutboxMessage.objects.filter(id=outbox_guard.message_id).first()
    assert db_message
    assert db_message.idempotency_key == idempotency_key
    assert db_message.aggregate_type == 'Mock'
    assert db_message.aggregate_id == str(aggregate_id)
    assert db_message.event_type == event_type
    assert db_message.payload == payload

    assert db_message.status == enums.EventStatuses.FAILED
    assert db_message.created_at is not None
    assert db_message.sent_at is None
    assert db_message.error == error


@pytest.mark.parametrize('strategy', [
    'celery_misc.transactional_outbox.strategies.DummyCheckStatusStrategy',
    'celery_misc.transactional_outbox.strategies.DummyBlockBatchStrategy',
])
def test_send_events__validate_status(mocker, strategy):
    """ Проверка статуса события при отправке """
    mocker.patch('celery_misc.transactional_outbox.settings.SEND_EVENTS_STRATEGY', strategy)
    message_kwargs = {
        'aggregate_type': 'Order',
        'aggregate_id': '123',
        'event_type': 'order.created',
        'payload': {'total': 100}
    }
    now = timezone.now()
    objs = models.OutboxMessage.objects.bulk_create([
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.PENDING, **message_kwargs),
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.SENT,
                             sent_at=now, **message_kwargs),
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.FAILED, error='error',
                             **message_kwargs),
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.EXPIRED, **message_kwargs)
    ])

    pending, sent, failed, expired = objs

    tasks.send_events.apply_async()

    pending.refresh_from_db()
    assert pending.sent_at is not None
    assert pending.status == enums.EventStatuses.SENT

    sent.refresh_from_db()
    assert sent.sent_at == now
    assert sent.status == enums.EventStatuses.SENT

    failed.refresh_from_db()
    assert failed.sent_at is not None
    assert failed.status == enums.EventStatuses.SENT

    expired.refresh_from_db()
    assert expired.sent_at is None
    assert expired.status == enums.EventStatuses.EXPIRED


def test_expiring_events():
    """ Периодическая задача которая помечает сообщения как устаревшие """
    message_kwargs = {
        'aggregate_type': 'Order',
        'aggregate_id': '123',
        'event_type': 'order.created',
        'payload': {'total': 100}
    }
    now = timezone.now()
    expiration_date = now - timedelta(hours=25)
    objs = models.OutboxMessage.objects.bulk_create([
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.PENDING,
                             created_at=now, **message_kwargs),
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.PENDING,
                             created_at=now, **message_kwargs),
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.PENDING,
                             created_at=now, **message_kwargs),
        models.OutboxMessage(idempotency_key=str(uuid6.uuid7()), status=enums.EventStatuses.PENDING,
                             created_at=now, **message_kwargs),
    ])
    event_1, expired_event_1, event_2, expired_event_2 = objs

    expired_event_1.created_at = expiration_date
    expired_event_1.save(update_fields=['created_at'])

    expired_event_2.created_at = expiration_date
    expired_event_2.save(update_fields=['created_at'])

    tasks.expiring_events.apply_async()

    event_1.refresh_from_db()
    assert event_1.status == enums.EventStatuses.PENDING

    expired_event_1.refresh_from_db()
    assert expired_event_1.status == enums.EventStatuses.EXPIRED

    event_2.refresh_from_db()
    assert event_2.status == enums.EventStatuses.PENDING

    expired_event_2.refresh_from_db()
    assert expired_event_2.status == enums.EventStatuses.EXPIRED

    event_1.created_at = expiration_date
    event_1.save(update_fields=['created_at'])

    tasks.delete_events.apply_async()

    assert models.OutboxMessage.objects.filter(id=event_2.id).exists()
    assert not models.OutboxMessage.objects.filter(id=event_1.id).exists()
    assert not models.OutboxMessage.objects.filter(id=expired_event_1.id).exists()
    assert not models.OutboxMessage.objects.filter(id=expired_event_2.id).exists()
