# Transactional outbox. Реализация паттерна Transactional Outbox с использованием Celery и Django

Обеспечивает работу базового алгоритма
паттерна [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html), оставляя детали
реализации на вашей стороне.

## Быстрый старт

1. Установите последнюю версию пакета или добавьте ее в requirements.txt

```
pip install celery-misc==1.0.2
```

2. Добавьте периодический запуск задач, используя django-celery-beat.

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'Периодическая отсылка сообщений': {
        'task': 'celery_misc.transactional_outbox.tasks.send_events',
        'schedule': crontab(minute='*/3'),  # every 3 min
    },
    'Пометка сообщений как устаревшие': {
        'task': 'celery_misc.transactional_outbox.tasks.expiring_events',
        'schedule': crontab(minute='*/20'),  # every 20 min
    },
    'Удаление устаревших сообщений': {
        'task': 'celery_misc.transactional_outbox.tasks.delete_events',
        'schedule': crontab(minute='*/20'),  # every 20 min
    },
}
```

``send_events`` - отсылает еще не отправленные сообщения

``expiring_events`` - помечает сообщения, которые не были отправлены за определенный период времени(по умолчанию 12
часов) как устаревшие

``delete_events`` - удаляет сообщения, которые были созданы позднее определенной даты(по умолчанию текущая дата минус 24
часа)

3. Добавьте нужные модули в настройках Django. django_json_widget нужен для красивого отображение json полей в Django
   AdminUI.

```python
INSTALLED_APPS = [
    ...,
    'celery_misc.transactional_outbox',
    'django_json_widget'
]
```

4. Выполнить миграции

```
python manage.py migrate transactional_outbox 
```

5. Настройте модуль, добавив в Django settings параметр ``CELERY_MISC_TRANSACTIONAL_OUTBOX``.

```python
CELERY_MISC_TRANSACTIONAL_OUTBOX = {
    'SEND_EVENTS_MAX_RETRIES': 6,
    'SEND_EVENTS_RETRY_BACKOFF': 4,
    'SEND_EVENTS_RETRY_BACKOFF_MAX': 800,
    'SEND_EVENTS_RETRY_JITTER': True,
    'SEND_EVENTS_STRATEGY': 'celery_misc.transactional_outbox.strategies.DummyCheckStatusStrategy'
}
```

``SEND_EVENTS_STRATEGY`` отвечает за стратегию отправки и реализацию самой отправки. Наследуйтесь от BlockBatchStrategy
или CheckStatusStrategy и реализуйте механизм отправки сообщений во внешнюю систему.

6. Вы прекрасны! Реализовывайте бизнес логику вашего приложения, не вдаваясь в детали Transactional Outbox.

## Основные возможности

1. Обеспечивает работу базового алгоритма
   паттерна [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)
2. Предоставляет API регистрации событий с дальнейшей их отправкой во внешнюю систему

```python
from celery_misc.transactional_outbox import outbox_utils, models, enums, tasks
from unittest.mock import Mock

with outbox_utils.OutboxEvent('order.created') as outbox_guard:
    # Здесь order - созданная связанная сущность
    order = Mock()
    order.id = 123
    payload = {'total': 100}
    idempotency_key = 'test1234'

    outbox_guard.send(order, payload, idempotency_key=idempotency_key)
```

3. Предоставляет API для реализации своей собственной стратегии отправки.
4. Возможность повторной отправки.
5. Предоставляет утилитарные задачи, поддерживающие актуальность событий и своевременную их удаление.
6. Предоставляет API регистрации пакета событий

```python
import uuid
from celery_misc.transactional_outbox import outbox_utils, models, enums, tasks
from unittest.mock import Mock

total_count = 100
payload = [{'i': i} for i in range(total_count)]
idempotency_key = [str(uuid.uuid4()) for _ in range(total_count)]
with outbox_utils.OutboxEvent('order.created') as outbox_guard:
    order = Mock()
    order.id = 123

    outbox_guard.send(order, payload, idempotency_key=idempotency_key)
```

7. Возможность указания стратегии обработки при создании событий или пакета событий. У каждого события может быть либо
   своя стратегии отправки, либо стратегия по умолчанию, заданная в настройке SEND_EVENTS_STRATEGY.

```python
import uuid
from celery_misc.transactional_outbox import outbox_utils, models, enums, tasks
from unittest.mock import Mock

strategy = 'celery_misc.transactional_outbox.strategies.DummyBlockBatchStrategy'
aggregate_id = 123
event_type = 'order.created'
payload = {'total': 100}
idempotency_key = str(uuid.uuid4())
meta_data = {
    'test': 12345
}
with outbox_utils.OutboxEvent(event_type, strategy=strategy) as outbox_guard:
    order = Mock()
    order.id = aggregate_id

    outbox_guard.send(order, payload, idempotency_key=idempotency_key, meta_data=meta_data)
```

при отправке события будет использоваться стратегия 
"celery_misc.transactional_outbox.strategies.DummyBlockBatchStrategy" даже если по умолчанию указана другая.

## Стратегии отправки

Существует две стратегии отправки сообщений во внешнюю систему - BlockBatchStrategy и CheckStatusStrategy.

**BlockBatchStrategy**. Стратегия блокирования всего пакета сообщений. В этом случае не нужно дополнительно проверять
статус сообщений и открывать отдельные транзакции, так как создается одна длительная транзакция. Batch_size желательно
уменьшить, чтобы сократить время общей блокировки.

**CheckStatusStrategy**. Стратегия отказа от одной долгой транзакции. В этом случае возможны ситуации, когда сообщения
уже были отправлены. Поэтому перед отправкой требуется блокировка записи с проверкой статуса. Batch_size можно
увеличить, так как нет одной длительной транзакции. При этом подходе записи OutboxMessage будут сразу доступны после их
обработки.

Наследуйтесь от BlockBatchStrategy или CheckStatusStrategy и реализуйте механизм отправки сообщений во внешнюю систему
путем переопределения метода publish_message. Например,

```python
from celery_misc.transactional_outbox import models
from celery_misc.transactional_outbox.strategies import BlockBatchStrategy, CheckStatusStrategy


class MyBlockBatchStrategy(BlockBatchStrategy):
    def publish_message(self, message: models.OutboxMessage):
        pass


class MyCheckStatusStrategy(CheckStatusStrategy):
    def publish_message(self, message: models.OutboxMessage):
        pass
```