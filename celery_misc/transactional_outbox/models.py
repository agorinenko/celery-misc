from django.db import models

from celery_misc.transactional_outbox import enums


class OutboxMessage(models.Model):
    """ OUTBOX """

    idempotency_key = models.CharField(null=False, blank=False, max_length=64, unique=True, db_index=True,
                                       verbose_name='Idempotency key')
    aggregate_type = models.CharField(null=False, blank=False, max_length=128, verbose_name='Тип агрегата',
                                      help_text='Например, название модели данных "Order".')
    aggregate_id = models.CharField(null=False, blank=False, max_length=64, verbose_name='ID агрегата',
                                    help_text='Например, ID экземпляра модели данных "164" или "8470df44-5e62-44db-8881-bfa9606b507c".')
    event_type = models.CharField(null=False, blank=False, max_length=128, verbose_name='Тип события',
                                  help_text='Например, "order.created".')
    payload = models.JSONField(null=False, blank=False, verbose_name='Данные события')
    status = models.CharField(max_length=50, null=False, blank=False,
                              choices=enums.EventStatuses.choices,
                              default=enums.EventStatuses.PENDING,
                              verbose_name='Статус отправки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отправки')

    error = models.TextField(null=True, blank=True, verbose_name='Ошибка отправки')

    class Meta:
        """ Meta """
        verbose_name = 'событие'
        verbose_name_plural = 'События'

    def __str__(self):
        return f'{self.aggregate_type}#{self.aggregate_id}'
