from django.db.models import Q

from celery_misc.celery_monitoring import enums
from django.db import models


class CeleryTaskInstanceQuerySet(models.QuerySet):
    """ CeleryTaskInstanceQuerySet """

    def active_tasks(self, reverse: bool | None = False):
        """ Получить активные задачи """
        task_filter = Q(task_status=enums.TaskStatuses.IN_PROGRESS)
        if reverse:
            return self.filter(~task_filter)

        return self.filter(task_filter)

    def revoke_tasks(self) -> int:
        return self.update(task_status=enums.TaskStatuses.REVOKED)


class CeleryTaskInstanceManager(models.Manager):
    """ CeleryTaskInstanceManager """

    def get_queryset(self):
        """ get query set """
        return CeleryTaskInstanceQuerySet(
            model=self.model,
            using=self._db,
            hints=self._hints)
