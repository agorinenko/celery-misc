import uuid

import pytest

from celery_misc.celery_monitoring import models as monitor_models, enums, monitoring_utils
from django_start.web_app import tasks

pytestmark = pytest.mark.django_db


def test_ping_task():
    """ Тестирование основного сценария запуска задачи """
    options = {
        'args': [1, 2, 3],
        'kwargs': {'timeout': 0}
    }
    result_task = tasks.ping.apply_async(**options)

    instance = monitor_models.CeleryTaskInstance.objects.filter(task_id=result_task.id).first()
    assert instance
    assert instance.task_args == options['args']
    assert instance.task_kwargs == options['kwargs']
    assert instance.task_name == 'django_start.web_app.tasks.ping'
    assert instance.task_status == enums.TaskStatuses.DONE
    assert instance.attempt_number == 1
    assert instance.duration > 0
    assert instance.duration == instance.calculate_duration()
    assert instance.finished_at is not None
    assert instance.started_at is not None
    assert instance.state is None
    assert instance.profiling_cpu_result is None
    assert instance.profiling_memory_result is None
    assert instance.result == {'data': 'pong'}


def test_error_task():
    """ Тестирование ошибочного сценария запуска задачи """
    options = {
        'args': [1, 2, 3],
        'kwargs': {'timeout': 0}
    }
    result_task = tasks.error_task.apply_async(**options)

    instance = monitor_models.CeleryTaskInstance.objects.filter(task_id=result_task.id).first()
    assert instance
    assert instance.task_args == options['args']
    assert instance.task_kwargs == options['kwargs']
    assert instance.task_name == 'django_start.web_app.tasks.error_task'
    assert instance.task_status == enums.TaskStatuses.ERROR
    assert instance.attempt_number == 4
    assert instance.duration > 0
    assert instance.duration == instance.calculate_duration()
    assert instance.finished_at is not None
    assert instance.started_at is not None
    assert instance.state is None
    assert instance.profiling_cpu_result is None
    assert instance.profiling_memory_result is None
    assert instance.result == {'error': 'Raise error.', 'traceback': 'NoneType: None\n'}


def test_restart_task():
    """ Тестирование сценария перезапуска задачи """
    options = {
        'args': [1, 2, 3],
        'kwargs': {'timeout': 0}
    }
    result_task = tasks.ping.apply_async(**options)

    instance = monitor_models.CeleryTaskInstance.objects.filter(task_id=result_task.id).first()

    restarted_task_id = monitoring_utils.restart_task(instance)

    instance.refresh_from_db()

    assert instance.restarted_task_id == uuid.UUID(restarted_task_id)

    instance = monitor_models.CeleryTaskInstance.objects.filter(task_id=restarted_task_id).first()
    assert instance
    assert instance.task_args == options['args']
    assert instance.task_kwargs == options['kwargs']
    assert instance.task_name == 'django_start.web_app.tasks.ping'
    assert instance.task_status == enums.TaskStatuses.DONE
    assert instance.attempt_number == 1
    assert instance.duration > 0
    assert instance.duration == instance.calculate_duration()
    assert instance.finished_at is not None
    assert instance.started_at is not None
    assert instance.state is None
    assert instance.profiling_cpu_result is None
    assert instance.profiling_memory_result is None
    assert instance.result == {'data': 'pong'}


def test_long_running_task():
    """ Тестирование длительных задач """
    options = {
        'args': [1, 2, 3],
        'kwargs': {'timeout': 0}
    }
    result_task = tasks.long_running.apply_async(**options)

    assert not monitor_models.CeleryTaskInstance.objects.all().active_tasks().exists()

    instance = monitor_models.CeleryTaskInstance.objects.filter(task_id=result_task.id).first()

    assert instance.task_status == enums.TaskStatuses.REVOKED
    assert instance.is_revoked
    assert instance.duration > 0
    assert instance.duration == instance.calculate_duration()
    assert instance.finished_at is not None
    assert instance.started_at is not None
