# Celery misc. Библиотека утилитарных модулей для Celery на Python

Помогает избавиться от дублирования кода и решает рутинные задачи при работе с Celery.

Структура проекта:

1. celery_misc.celery_monitoring - модуль мониторинга
2. celery_misc.transactional_outbox - модуль transactional outbox
3. django_start - тестовый Django проект

## Celery Monitoring: Модуль мониторинга задач Celery с интеграцией в Django Admin

Компонент обеспечивает наблюдение за запущенными задачами Celery, ведет историю их выполнения и предоставляет функционал
поиска по историческим данным. Решение отличается простотой подключения и не требует развертывания дополнительной
инфраструктуры. Полная документация представлена в разделе celery_monitoring.

## Transactional outbox. Реализация паттерна Transactional Outbox с использованием Celery и Django

Обеспечивает работу базового алгоритма
паттерна [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html), оставляя детали
реализации на вашей стороне. Полная документация доступна в разделе transactional_outbox.

**Ожидается в 1.0.2**