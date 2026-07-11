import logging
import traceback

import psutil
from celery.signals import task_prerun, task_postrun
from django.utils import timezone

from celery_misc.celery_monitoring import models, enums, monitoring_utils
from celery_misc.celery_utils import cleanup_db_connections

logger = logging.getLogger(__name__)


@task_prerun.connect
@cleanup_db_connections
def register_task(task_id, task, *args, **kwargs):
    """ Регистрация запущенной задачи Celery """
    if monitoring_utils.TASK_REPOSITORY.is_monitoring(task.name):
        now = timezone.now()
        fields = {
            'task_args': kwargs['args'],
            'task_kwargs': kwargs['kwargs'],
            'task_name': task.name,
            'started_at': now,
            'attempt_number': 1
        }
        profiling_memory_result = None
        if monitoring_utils.TASK_REPOSITORY.is_profiling_memory(task.name):
            rss = _get_memory_usage()
            profiling_memory_result = {
                'rss_memory_before': rss
            }
            fields['profiling_memory_result'] = profiling_memory_result

        task_row, created = models.CeleryTaskInstance.objects.get_or_create(task_id=task_id, defaults=fields)
        if not created:
            attempt_number = task_row.attempt_number or 1
            properties = {
                'task_status': enums.TaskStatuses.IN_PROGRESS,
                'started_at': now,
                'finished_at': None,
                'attempt_number': attempt_number + 1,
                'duration': 0
            }

            if profiling_memory_result:
                properties['profiling_memory_result'] = profiling_memory_result

            monitoring_utils.update_task_properties(task_row, properties)


@task_postrun.connect
@cleanup_db_connections
def finish_task(task_id, task, retval, *args, **kwargs):
    """ Регистрация окончания запущенной задачи Celery """
    if monitoring_utils.TASK_REPOSITORY.is_monitoring(task.name):
        task_status = enums.TaskStatuses.DONE
        task_result = {}
        if retval:
            if isinstance(retval, dict):
                task_result = retval
            elif isinstance(retval, Exception):
                task_status = enums.TaskStatuses.ERROR

                task_result = {
                    'error': str(retval),
                    'traceback': str(traceback.format_exc())
                }
            else:
                task_result = {
                    'data': str(retval)
                }

        _update_task_status(task.name, task_id, task_status, task_result)


def _update_task_status(task_name, task_id, task_status, task_result):
    task_row = models.CeleryTaskInstance.objects.filter(task_id=task_id).first()
    if task_row:
        properties = {
            'result': task_result,
            'finished_at': timezone.now()
        }
        if task_row.task_status != enums.TaskStatuses.REVOKED:
            properties['task_status'] = task_status

        if monitoring_utils.TASK_REPOSITORY.is_profiling_memory(task_name):
            rss = _get_memory_usage()
            profiling_memory_result = task_row.profiling_memory_result
            profiling_memory_result['rss_memory_after'] = rss
            profiling_memory_result['rss_memory_usage'] = rss - profiling_memory_result['rss_memory_before']

            properties['profiling_memory_result'] = profiling_memory_result

        monitoring_utils.update_task_properties(task_row, properties)


def _get_memory_usage() -> float | int:
    """ Точное измерение использования памяти """
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024  # Resident Set Size - физическая память
