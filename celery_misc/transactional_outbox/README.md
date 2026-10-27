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
    'Возврат зависших сообщений в очередь': {
        'task': 'celery_misc.transactional_outbox.tasks.requeue_stale_events',
        'schedule': crontab(minute='*/5'),  # every 5 min
    },
}
```

### Задачи и их настройки

| Задача | Что делает | Параметры вызова | Настройки |
|---|---|---|---|
| ``send_events`` | Периодически отсылает ещё не отправленные сообщения (страховка; основной путь — немедленная отправка) | ``event_ids`` — отправить только указанные сообщения; ``suppress_events_error`` — не падать при ошибках отправки; ``batch_size`` — размер порции (по умолчанию 50) | ``SEND_EVENTS_STRATEGY`` — стратегия по умолчанию; ``SEND_EVENTS_ALLOWED_STRATEGIES`` — whitelist разрешённых стратегий (не попавшие в него помечаются ``failed``) |
| ``send_events_only_ones`` | Отправляет созданные события сразу после их регистрации (диспатчится автоматически после коммита транзакции) | ``event_ids`` — обязательный список сообщений | ``SEND_EVENTS_MAX_RETRIES`` (5), ``SEND_EVENTS_RETRY_BACKOFF`` (3), ``SEND_EVENTS_RETRY_BACKOFF_MAX`` (600), ``SEND_EVENTS_RETRY_JITTER`` (True) — политика ретраев при ошибках отправки |
| ``expiring_events`` | Помечает сообщения, не отправленные за определённый период (по умолчанию 12 часов), как устаревшие | ``expiration_delta_in_hours`` (по умолчанию 12) | — |
| ``delete_events`` | Удаляет сообщения, созданные ранее определённой даты (по умолчанию старше 24 часов) | ``expiration_delta_in_hours`` (по умолчанию 24) | — |
| ``requeue_stale_events`` | Возвращает сообщения, «зависшие» в статусе ``sending`` дольше допустимого времени (падение воркера между захватом и отправкой), обратно в ``pending`` | ``stale_delta_minutes`` (по умолчанию берётся из настройки) | ``REQUEUE_STALE_EVENTS_MINUTES`` (по умолчанию 10) — порог «зависания»; должен быть больше максимальной длительности публикации |

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
    'SEND_EVENTS_STRATEGY': 'celery_misc.transactional_outbox.strategies.DummyCheckStatusStrategy',
    'SEND_EVENTS_ALLOWED_STRATEGIES': [
        'celery_misc.transactional_outbox.strategies.DummyCheckStatusStrategy',
    ],
    'REQUEUE_STALE_EVENTS_MINUTES': 10,
}
```

``SEND_EVENTS_STRATEGY`` отвечает за стратегию отправки и реализацию самой отправки. Наследуйтесь от BlockBatchStrategy
или CheckStatusStrategy и реализуйте механизм отправки сообщений во внешнюю систему.

``SEND_EVENTS_ALLOWED_STRATEGIES`` — whitelist стратегий, которые разрешено загружать по FQCN. Стратегия, не входящая
в список, не импортируется и не исполняется: её сообщения помечаются статусом ``failed`` с текстом ошибки. Пустой
список означает отсутствие ограничений (совместимость с прежним поведением).

``REQUEUE_STALE_EVENTS_MINUTES`` задаёт порог, после которого сообщение, застрявшее в статусе ``sending``, считается
«зависшим» и возвращается задачей ``requeue_stale_events`` в ``pending``. Значение должно быть заведомо больше
максимальной длительности публикации (внешнего вызова).

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

**CheckStatusStrategy**. Стратегия без долгих блокировок: сообщение захватывается атомарным условным UPDATE
(`pending`/`failed` → `sending`), публикация выполняется **вне** транзакции, а финальный статус (`sent`/`failed`)
пишется отдельным коротким UPDATE. Двойная отправка исключается условием захвата: перевести строку в `sending` может
только один воркер (`rowcount == 1`). Сообщения, «зависшие» в `sending` из-за падения воркера между захватом и
финализацией, возвращает в `pending` периодическая задача ``requeue_stale_events``.

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