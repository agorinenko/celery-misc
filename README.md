# Celery misc. Библиотека утилитарных модулей для Celery на Python

Помогает избавиться от дублирования кода и решает рутинные задачи при работе с Celery.

Структура проекта:

1. celery_misc.celery_monitoring - модуль мониторинга
2. celery_misc.transactional_outbox - модуль transactional outbox
3. celery_misc.celery_utils - утилиты для задач Celery и Django
4. django_start - тестовый Django проект

## Установка

```bash
pip install celery-misc           # только celery, без django
pip install http-misc[django]     # для проектов celery + django
```

## Celery Monitoring: Модуль мониторинга задач Celery с интеграцией в Django Admin

Компонент обеспечивает наблюдение за запущенными задачами Celery, ведет историю их выполнения и предоставляет функционал
поиска по историческим данным. Решение отличается простотой подключения и не требует развертывания дополнительной
инфраструктуры. Полная документация представлена в разделе [celery_monitoring](https://github.com/agorinenko/celery-misc/blob/main/celery_misc/celery_monitoring/README.md).

## Transactional outbox. Реализация паттерна Transactional Outbox с использованием Celery и Django

Обеспечивает работу базового алгоритма
паттерна [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html), оставляя детали
реализации на вашей стороне. Полная документация доступна в разделе [transactional_outbox](https://github.com/agorinenko/celery-misc/blob/main/celery_misc/transactional_outbox/README.md).

## Celery utils. Утилиты для задач Celery и Django

`cleanup_db_connections` проверяет соединения с БД перед выполнением задачи и повторяет операцию, если она упала
из-за ошибки соединения. Восстановленные сбои логируются как WARNING, ERROR пишется только при неудачном повторе.

При использовании psycopg_pool соединения, разорванные БД в простое (рестарт, failover, сетевой сбой), могут
оставаться в пуле и выдаваться задачам. Когда `check_connections` обнаруживает неработоспособное соединение, он
закрывает его и очищает пул (`pool.check()`), чтобы следующая задача не получила другое мёртвое соединение.

Библиотека не включает health check пула автоматически. Для дополнительной защиты рекомендуется включить его
на стороне Django:

```python
DATABASES = {
    'default': {
        # ...
        'CONN_HEALTH_CHECKS': True,
    },
}
```
