def signals_connect():
    """Connect to signals."""
    from django.db.models import signals
    from celery_misc.celery_monitoring import models
    # CeleryTaskRepository
    signals.post_save.connect(
        update_repository_signal, sender=models.CeleryTaskRepository, weak=True,
        dispatch_uid='post_save__CeleryTaskRepository_update_repository_for'
    )
    signals.post_delete.connect(
        update_repository_signal, sender=models.CeleryTaskRepository, weak=True,
        dispatch_uid='post_delete__CeleryTaskRepository_update_repository_for'
    )
    # TaskBlackList
    signals.post_save.connect(
        update_repository_signal, sender=models.TaskBlackList, weak=True,
        dispatch_uid='post_save__TaskBlackList_update_repository_for'
    )
    signals.post_delete.connect(
        update_repository_signal, sender=models.TaskBlackList, weak=True,
        dispatch_uid='post_delete__TaskBlackList_update_repository_for'
    )
    # TaskWhiteList
    signals.post_save.connect(
        update_repository_signal, sender=models.TaskWhiteList, weak=True,
        dispatch_uid='post_save__TaskWhiteList_update_repository_for'
    )
    signals.post_delete.connect(
        update_repository_signal, sender=models.TaskWhiteList, weak=True,
        dispatch_uid='post_delete__TaskWhiteList_update_repository_for'
    )


def update_repository_signal(*args, **kwargs):
    """ Обновление глобального репозитория задач """
    from celery_misc.celery_monitoring.monitoring_utils import TASK_REPOSITORY

    TASK_REPOSITORY.refresh_state()
