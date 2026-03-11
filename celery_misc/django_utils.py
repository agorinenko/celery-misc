import logging
from typing import Any

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import IntegrityError
from django.db.models import JSONField
from django.http import HttpResponseRedirect
from django_json_widget.widgets import JSONEditorWidget


def import_from_settings(name: str, default: Any | None = None):
    """ Загрузка конфигурационного параметра """
    try:
        return getattr(settings, name, default)
    except AttributeError:
        raise ImproperlyConfigured(f'Параметр {name} не найден.')


class UserFriendlyModelAdmin(admin.ModelAdmin):
    """
    Вывод ошибки пользователю вместо 500 ошибки сервера в административном интерфейсе
    """
    formfield_overrides = {JSONField: {'widget': JSONEditorWidget}}

    @csrf_protect_m
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except (ValidationError, IntegrityError) as ex:
            if hasattr(ex, 'messages') and ex.messages:
                for message in ex.messages:
                    self.message_user(request, message, level=logging.ERROR)
            elif hasattr(ex, 'message') and ex.message:
                self.message_user(request, ex.message, level=logging.ERROR)
            else:
                self.message_user(request, str(ex), level=logging.ERROR)

            return HttpResponseRedirect(request.path)
