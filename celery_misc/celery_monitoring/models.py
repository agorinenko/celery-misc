from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from celery_misc.celery_monitoring import enums, query_sets


class CeleryTaskRepository(models.Model):
    """ Репозиторий задач """
    name = models.CharField(null=False, blank=False, unique=True, max_length=200,
                            verbose_name='Наименование задачи',
                            help_text='Например: "web_app.tasks.send_emails"')

    extra_settings = models.JSONField(null=True, blank=True, verbose_name='Настройки задачи')

    enabled = models.BooleanField(default=True, null=False, blank=False, verbose_name='Разрешена')

    is_profiling_cpu = models.BooleanField(default=False, null=False, blank=False,
                                           verbose_name='Доступно профилирование CPU')
    is_profiling_memory = models.BooleanField(default=False, null=False, blank=False,
                                              verbose_name='Доступно профилирование ОЗУ')

    class Meta:
        """ Meta """
        verbose_name = 'Репозиторий задач'
        verbose_name_plural = 'Репозиторий задач'

    def __str__(self):
        return self.name


# TODO: Возможность отключения по времени(в том числе несколько периодов)
class TaskWhiteList(models.Model):
    """ Белый список задач """
    task = models.OneToOneField(CeleryTaskRepository, null=False, blank=False, on_delete=models.CASCADE,
                                related_name='white', verbose_name='Задача')

    class Meta:
        """ Meta """
        verbose_name = 'Белый список задач'
        verbose_name_plural = 'Белый список задач'

    def __str__(self):
        return self.task.name


class TaskBlackList(models.Model):
    """ Черный список задач """
    task = models.OneToOneField(CeleryTaskRepository, null=False, blank=False, on_delete=models.CASCADE,
                                related_name='black', verbose_name='Задача')

    class Meta:
        """ Meta """
        verbose_name = 'Черный список задач'
        verbose_name_plural = 'Черный список задач'

    def __str__(self):
        return self.task.name


class CeleryTaskInstance(models.Model):
    """ История выполнения задач Celery """
    objects = query_sets.CeleryTaskInstanceManager()

    @property
    def is_revoked(self):
        """ Задача отозвана """
        return self.task_status == enums.TaskStatuses.REVOKED

    attempt_number = models.PositiveIntegerField(null=True, blank=True, default=0,
                                                 verbose_name='Количество попыток выполнения')
    task_args = models.JSONField(null=True, blank=True, verbose_name='Аргументы запуска')
    task_kwargs = models.JSONField(null=True, blank=True, verbose_name='Параметры запуска')
    state = models.JSONField(null=True, blank=True, verbose_name='Состояние выполнения')
    result = models.JSONField(null=True, blank=True, verbose_name='Результат выполнения')
    profiling_cpu_result = models.TextField(null=True, blank=True, verbose_name='Результат профилирования CPU')
    profiling_memory_result = models.TextField(null=True, blank=True, verbose_name='Результат профилирования ОЗУ')

    task_id = models.UUIDField(unique=True, null=False, blank=False, verbose_name='ID задачи')
    restarted_task_id = models.UUIDField(null=True, blank=True, verbose_name='ID перезапущенной задачи')
    task_name = models.CharField(null=False, blank=False, verbose_name='Наименование задачи')
    started_at = models.DateTimeField(null=False, blank=False, verbose_name='Дата начала выполнения')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата окончания выполнения')
    duration = models.FloatField(null=True, validators=[MinValueValidator(0.0)], blank=True,
                                 verbose_name='Продолжительность выполнения задачи, сек')
    task_status = models.CharField(max_length=50, null=False, blank=False,
                                   choices=enums.TaskStatuses.choices,
                                   default=enums.TaskStatuses.IN_PROGRESS,
                                   verbose_name='Статус выполнения задачи')

    def calculate_duration(self) -> float:
        """ Продолжительность выполнения задачи """
        if self.started_at:
            finished_at = self.finished_at or timezone.now()
            diff = finished_at - self.started_at
            return diff.total_seconds()

        return 0

    def update_duration(self):
        """ Обновление продолжительности выполнения задачи """
        self.duration = self.calculate_duration()
        self.save(update_fields=['duration'])

    def revoke_task(self):
        self.task_status = enums.TaskStatuses.REVOKED
        self.save(update_fields=['task_status'])

    class Meta:
        """ Meta """
        verbose_name = 'информация о выполнении задачи'
        verbose_name_plural = 'Информация о выполнении задачи'

    def __str__(self):
        return f'{self.task_name} ({self.task_id})'
