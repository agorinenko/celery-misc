import logging
import traceback

from celery.signals import task_prerun, task_postrun
from django.utils import timezone

from celery_misc.celery_monitoring import models, enums, monitoring_utils
from celery_misc.celery_utils import cleanup_db_connections

logger = logging.getLogger(__name__)


@task_prerun.connect
@cleanup_db_connections
def register_task(task_id, task, *args, **kwargs):
    """ Регистрация запущенной задачи Celery """
    if monitoring_utils.TASK_REPOSITORY.is_monitoring(task, *args, **kwargs):
        now = timezone.now()
        fields = {
            'task_args': kwargs['args'],
            'task_kwargs': kwargs['kwargs'],
            'task_name': task.name,
            'started_at': now,
            'attempt_number': 1
        }
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

            monitoring_utils.update_task_properties(task_row, properties)


@task_postrun.connect
@cleanup_db_connections
def finish_task(task_id, task, retval, *args, **kwargs):
    """ Регистрация окончания запущенной задачи Celery """
    if monitoring_utils.TASK_REPOSITORY.is_monitoring(task, *args, **kwargs):
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

        _update_task_status(task_id, task_status, task_result)


def _update_task_status(task_id, task_status, task_result):
    task_row = models.CeleryTaskInstance.objects.filter(task_id=task_id).first()
    if task_row:
        properties = {
            'result': task_result,
            'finished_at': timezone.now()
        }
        if task_row.task_status != enums.TaskStatuses.REVOKED:
            properties['task_status'] = task_status

        monitoring_utils.update_task_properties(task_row, properties)
