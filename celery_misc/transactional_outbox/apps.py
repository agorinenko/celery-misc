# pylint: disable=all
from django.apps import AppConfig


class TransactionalOutboxConfig(AppConfig):
    """ TransactionalOutboxConfig """
    name = 'celery_misc.transactional_outbox'
    verbose_name = 'Transactional outbox'

    def ready(self):
        try:
            super().ready()
        except ImportError:
            pass
