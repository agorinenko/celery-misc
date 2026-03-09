import uuid

import pytest
from django.utils import timezone

from celery_misc.celery_monitoring import enums, models, tasks

pytestmark = pytest.mark.django_db


def test_delete_running_log():
    """ Зачистка лога выполненных задач за прошедший период """
    options = {
        'args': [1, 2, 3],
        'kwargs': {'timeout': 0}
    }
    for i in range(10):
        fields = {
            'task_args': options['args'],
            'task_kwargs': options['kwargs'],
            'task_name': f'Task {i}',
            'task_id': str(uuid.uuid4()),
            'started_at': timezone.now(),
            'attempt_number': 1
        }
        models.CeleryTaskInstance.objects.create(**fields)

    assert models.CeleryTaskInstance.objects.all().exists()
    task_name = 'celery_misc.celery_monitoring.tasks.delete_running_log_task'
    result_task = tasks.delete_running_log_task.apply_async(
        kwargs={'expiration_delta_in_hours': 0, 'force_delete': True}
    )
    assert not models.CeleryTaskInstance.objects.exclude(task_name=task_name).exists()
    instance = models.CeleryTaskInstance.objects.filter(task_id=result_task.id).first()
    assert instance
    assert instance.task_status == enums.TaskStatuses.DONE
    assert instance.duration > 0
