# pylint: disable=all
from django.apps import AppConfig


class CeleryMonitoringConfig(AppConfig):
    """ CeleryMonitoringConfig """
    name = 'celery_misc.celery_monitoring'
    verbose_name = 'Мониторинг задач'

    def ready(self):
        try:
            super().ready()
            from celery_misc.celery_monitoring import task_signals
            from celery_misc.celery_monitoring import tasks
            from celery_misc.celery_monitoring.signals import signals_connect
            signals_connect()
        except ImportError:
            pass
