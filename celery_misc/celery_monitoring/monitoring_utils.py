import logging
import uuid
from datetime import timedelta
from typing import Any

from celery import Task
from django.db.models import Q
from django.db.models.signals import post_delete
from django.utils import timezone
from kombu.utils import symbol_by_name

from celery_misc.celery_monitoring import models, enums
from celery_misc import model_utils, utils, signal_utils
from celery_misc.celery_monitoring.signals import update_repository_signal

logger = logging.getLogger(__name__)


def update_task_properties(task_obj: str | uuid.UUID | models.CeleryTaskInstance | Task, properties: dict[str, Any]):
    """ Обновление свойств задачи """
    if not isinstance(task_obj, models.CeleryTaskInstance):
        task_obj = find_task(task_obj)

    if task_obj:
        update_fields = []
        for field, value in properties.items():
            if hasattr(task_obj, field):
                update_fields.append(field)
                setattr(task_obj, field, value)

        if 'duration' not in properties:
            current_duration = task_obj.calculate_duration()
            if task_obj.duration:
                current_duration = task_obj.duration + current_duration
            task_obj.duration = current_duration
            update_fields.append('duration')

        task_obj.save(update_fields=update_fields)

        return True

    return False


def restart_task(task_obj: str | uuid.UUID | models.CeleryTaskInstance | Task) -> str | None:
    """ Перезапуск задачи """
    if not isinstance(task_obj, models.CeleryTaskInstance):
        task_obj = find_task(task_obj)

    if task_obj:
        if task_obj.task_status == enums.TaskStatuses.IN_PROGRESS:
            raise Exception('Выбранная задача находится в работе. Дождитесь ее завершения и повторите попытку.')

        task_func = symbol_by_name(task_obj.task_name)
        result_task = task_func.apply_async(args=task_obj.task_args, kwargs=task_obj.task_kwargs)
        task_obj.restarted_task_id = result_task.id
        task_obj.task_status = enums.TaskStatuses.RESTARTED
        task_obj.save(update_fields=['restarted_task_id', 'task_status'])

        return result_task.id

    return None


def save_state(task_obj: str | uuid.UUID | models.CeleryTaskInstance | Task,
               state: dict | None = None) -> models.CeleryTaskInstance:
    """ Сохранение состояния задачи """
    if not isinstance(task_obj, models.CeleryTaskInstance):
        task_obj = find_task(task_obj)

    if task_obj:
        task_obj.state = state
        task_obj.save(update_fields=['state'])
        return task_obj

    raise models.CeleryTaskInstance.DoesNotExist('Задача не найдена.')


def load_state(task_obj: str | uuid.UUID | models.CeleryTaskInstance | Task) -> dict:
    """ Загрузка состояния задачи """
    if not isinstance(task_obj, models.CeleryTaskInstance):
        task_obj = find_task(task_obj)

    if task_obj:
        return task_obj.state

    raise models.CeleryTaskInstance.DoesNotExist('Задача не найдена.')


def find_task(task_id: str | uuid.UUID | Task) -> models.CeleryTaskInstance | None:
    """ Поиск связанного объекта CeleryTaskInstance"""
    if isinstance(task_id, Task):
        task_id = task_id.request.id

    task_obj = models.CeleryTaskInstance.objects.filter(task_id=task_id).first()

    return task_obj


def delete_tasks_log(task, expiration_delta_in_hours: int | None = None,
                     force_delete: bool | None = False) -> int:
    """ Зачистка лога выполненных задач за прошедший период """
    expiration_delta_in_hours = expiration_delta_in_hours or 24
    if expiration_delta_in_hours > 0:
        expiration_date = timezone.now() - timedelta(hours=expiration_delta_in_hours)
        delete_filter = Q(started_at__lt=expiration_date)
    else:
        delete_filter = Q()

    if not force_delete:
        delete_filter &= ~Q(task_status=enums.TaskStatuses.IN_PROGRESS)

    task_id = task.request.id
    terminator = Terminator(task_id)
    delete_filter &= ~Q(task_id=task_id)

    queryset = models.CeleryTaskInstance.objects.filter(delete_filter)
    return model_utils.batch_delete(queryset, delete_filter, terminator=terminator)


class Terminator:
    def __init__(self, task_id):
        self.task_id = task_id

    def __call__(self, *args, **kwargs):
        task_row = find_task(self.task_id)
        if task_row:
            return task_row.is_revoked

        return False


def _normalize_name(name: str):
    name = name.lower().strip()
    return name


class TaskRepository(metaclass=utils.SingletonMeta):
    """ Репозиторий зарегистрированных задач """

    def __init__(self):
        self._task_repository = {}
        self._white_list = set()
        self._black_list = set()
        self._is_initialized = False

    def _ensure_initialized(self):
        """Ленивая инициализация репозитория"""
        if not self._is_initialized:
            self.refresh_state()
            self._is_initialized = True

    def is_profiling_memory(self, name: str) -> bool:
        """ Доступно профилирование ОЗУ """
        self._ensure_initialized()
        name = _normalize_name(name)
        task = self._task_repository.get(name)
        if not task:
            return False

        return task.get('is_profiling_memory', False)

    def is_profiling_cpu(self, name: str) -> bool:
        """ Доступно профилирование CPU """
        self._ensure_initialized()
        name = _normalize_name(name)
        task = self._task_repository.get(name)
        if not task:
            return False

        return task.get('is_profiling_cpu', False)

    def is_monitoring(self, name: str, log_info: bool | None = True) -> bool:
        """ Задание на мониторинге """
        self._ensure_initialized()
        name = _normalize_name(name)
        # Если репозиторий пуст, то для мониторинга доступны все задачи
        if not self._task_repository:
            return True

        # Если задача в черном списке, то она не доступна для мониторинга
        if name in self._black_list:
            if log_info:
                logger.info('Задача "%s" находится в черном списке.', name)
            return False

        # Если белый список ведется и задача в нем, то она доступна для мониторинга
        if self._white_list and name not in self._white_list:
            if log_info:
                logger.info('Открыт белый список и задача "%s" не находится в нем.', name)
            return False

        return True

    def refresh_state(self):
        """ Обновление состояния глобального репозитория задач """
        self._task_repository = {
            _normalize_name(i.name): {
                'name': i.name,
                'is_profiling_cpu': i.is_profiling_cpu,
                'is_profiling_memory': i.is_profiling_memory
            } for i in models.CeleryTaskRepository.objects.filter(enabled=True)}
        self._white_list = {_normalize_name(i.task.name) for i in
                            models.TaskWhiteList.objects.filter(task__enabled=True)}
        self._black_list = {_normalize_name(i.task.name) for i in
                            models.TaskBlackList.objects.filter(task__enabled=True)}

    def register(self, name: str) -> models.CeleryTaskRepository:
        """ Регистрация задачи """
        task, created = _get_or_create(models.CeleryTaskRepository, name=name)
        if created:
            self.refresh_state()

        return task

    def add_to_white_list(self, name: str) -> models.TaskWhiteList:
        """ Добавление в белый список """
        task, created_1 = _get_or_create(models.CeleryTaskRepository, name=name)
        obj, created_2 = _get_or_create(models.TaskWhiteList, task=task)
        if created_1 or created_2:
            self.refresh_state()

        return obj

    def remove_from_white_list(self, name: str) -> bool:
        """ Удаление из белого списка """
        with signal_utils.DisableSignal(post_delete, update_repository_signal, sender=models.TaskWhiteList, weak=True,
                                        dispatch_uid='post_delete__TaskWhiteList_update_repository_for'):
            num_deleted, _ = models.TaskWhiteList.objects.filter(task__name=name).delete()

        if num_deleted > 0:
            self.refresh_state()

        return num_deleted > 0

    def add_to_black_list(self, name: str) -> models.TaskBlackList:
        """ Добавление в черный список """
        task, created_1 = _get_or_create(models.CeleryTaskRepository, name=name)
        obj, created_2 = _get_or_create(models.TaskBlackList, task=task)
        if created_1 or created_2:
            self.refresh_state()
        return obj

    def remove_from_black_list(self, name: str) -> bool:
        """ Удаление из черного списка """
        with signal_utils.DisableSignal(post_delete, update_repository_signal, sender=models.TaskBlackList, weak=True,
                                        dispatch_uid='post_delete__TaskBlackList_update_repository_for'):
            num_deleted, _ = models.TaskBlackList.objects.filter(task__name=name).delete()

        if num_deleted > 0:
            self.refresh_state()

        return num_deleted > 0

    def remove_register(self, name: str) -> bool:
        """ Удаление регистрации задачи """
        with signal_utils.disable_signals([
            signal_utils.DisableSignal(post_delete, update_repository_signal, sender=models.CeleryTaskRepository,
                                       weak=True,
                                       dispatch_uid='post_delete__CeleryTaskRepository_update_repository_for'),
            signal_utils.DisableSignal(post_delete, update_repository_signal, sender=models.TaskBlackList, weak=True,
                                       dispatch_uid='post_delete__TaskBlackList_update_repository_for'),
            signal_utils.DisableSignal(post_delete, update_repository_signal, sender=models.TaskWhiteList, weak=True,
                                       dispatch_uid='post_delete__TaskWhiteList_update_repository_for')
        ]):
            num_deleted, _ = models.CeleryTaskRepository.objects.filter(name=name).delete()

        if num_deleted > 0:
            self.refresh_state()

        return num_deleted > 0

    def get_task_record(self, name: str) -> models.CeleryTaskRepository:
        """ Получение записи из репозитория задач """
        self._ensure_initialized()
        if name not in self._task_repository:
            raise ValueError(f'Задача "{name}" не найдена в репозитории.')

        return models.CeleryTaskRepository.objects.get(name=name)


TASK_REPOSITORY = TaskRepository()

ModelsList = models.TaskWhiteList | models.TaskBlackList | models.CeleryTaskRepository


def _get_or_create(modal_class: type[ModelsList], defaults: dict[str, Any] | None = None,
                   **kwargs: Any) -> tuple[ModelsList, bool]:
    """ Аналог get_or_create. Используем bulk_create для отключения сигналов """
    obj = modal_class.objects.filter(**kwargs).first()
    if obj:
        return obj, False
    if defaults is None:
        defaults = {}
    defaults.update(kwargs)
    objs = modal_class.objects.bulk_create([
        modal_class(**defaults)
    ])
    return objs[0], True
