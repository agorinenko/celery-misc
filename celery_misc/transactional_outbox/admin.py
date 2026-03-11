import logging

from django.contrib import admin
from django.http import HttpResponseRedirect

from celery_misc.django_utils import UserFriendlyModelAdmin
from celery_misc.transactional_outbox import models, outbox_utils


@admin.action(description='Повторная отправка сообщений')
def resend_events(self, request, queryset):  # pylint: disable=unused-argument
    """ Повторная отправка сообщений """
    event_ids = list(queryset.values_list('id', flat=True))
    outbox_utils.resend_events(event_ids)

    self.message_user(request, 'Повторная отправка сообщений выполнена.', level=logging.INFO)
    return HttpResponseRedirect(request.path)


@admin.register(models.OutboxMessage)
class CeleryTaskRepositoryAdmin(UserFriendlyModelAdmin):
    """ Admin model for OutboxMessage """
    actions = (resend_events,)
    list_display = ('aggregate_type', 'aggregate_id', 'event_type', 'created_at', 'sent_at')
    list_filter = ('status',)
    search_fields = ('aggregate_type', 'aggregate_id', 'event_type', 'idempotency_key')
