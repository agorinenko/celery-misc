from django.db import models


class TaskStatuses(models.TextChoices):
    """ Статусы задач Celery """
    IN_PROGRESS = 'in_progress', 'Выполняется'
    RESTARTED = 'restarted', 'Перезапущено'
    DONE = 'done', 'Завершена'
    ERROR = 'error', 'Ошибка выполнения'
    REVOKED = 'REVOKED', 'Отозвана'