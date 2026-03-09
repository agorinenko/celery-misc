import logging
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import JSONField, TextField
from django.db.models.functions import Cast
from django.http import HttpResponseRedirect
from django_json_widget.widgets import JSONEditorWidget

from celery_misc.celery_monitoring import models, monitoring_utils


@admin.action(description='Перезапустить задачу')
def restart_task(self, request, queryset):
    """ Перезапустить задачу """
    if queryset.count() > 1:
        self.message_user(request, 'Необходимо выбрать только одну задачу для перезапуска.', level=logging.ERROR)
        return HttpResponseRedirect(request.path)

    if queryset.count() == 1:
        db_task = queryset.first()
        monitoring_utils.restart_task(db_task)

    self.message_user(request, 'Задача успешно запущена.', level=logging.INFO)
    return HttpResponseRedirect(request.path)


@admin.action(description='Завершить задачи')
def kill_tasks(self, request, queryset):  # pylint: disable=unused-argument
    """ Завершить задачи """
    queryset.revoke_tasks()

    self.message_user(request, 'Задачи помечены для завершения.', level=logging.INFO)
    return HttpResponseRedirect(request.path)


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


@admin.register(models.CeleryTaskInstance)
class CeleryTaskInstanceAdmin(UserFriendlyModelAdmin):
    """ Admin model for CeleryTaskInstance """
    formfield_overrides = {JSONField: {'widget': JSONEditorWidget}}
    actions = (kill_tasks, restart_task)
    list_display = ('task_id', 'task_name', 'started_at', 'finished_at', 'task_status', 'duration')
    list_filter = ('task_status', 'task_name')
    search_fields = ('task_id', 'task_name', 'task_args_text', 'task_kwargs_text')
    ordering = ('-started_at', '-id')

    def get_search_results(self, request, queryset, search_term):
        """ Расширяем стандартный поиск для поиска по аннотированным полям """
        queryset = queryset.annotate(
            task_args_text=Cast('task_args', TextField()),
            task_kwargs_text=Cast('task_kwargs', TextField())
        )

        return super().get_search_results(request, queryset, search_term)


@admin.register(models.CeleryTaskRepository)
class CeleryTaskRepositoryAdmin(UserFriendlyModelAdmin):
    """ Admin model for CeleryTaskRepository """
    list_display = ('name', 'is_profiling_cpu', 'is_profiling_memory')
    list_filter = ('is_profiling_cpu', 'is_profiling_memory')
    search_fields = ('name',)


class TaskBaseListAdmin(UserFriendlyModelAdmin):
    """ Admin model for TaskWhiteList """
    list_display = ('task__name',)
    search_fields = ('task_name',)

    def get_search_results(self, request, queryset, search_term):
        """ Расширяем стандартный поиск для поиска по аннотированным полям """
        queryset = queryset.annotate(
            task_name=Cast('task__name', TextField()),
        )

        return super().get_search_results(request, queryset, search_term)


@admin.register(models.TaskWhiteList)
class TaskWhiteListAdmin(TaskBaseListAdmin):
    """ Admin model for TaskWhiteList """


@admin.register(models.TaskBlackList)
class TaskBlackListAdmin(TaskBaseListAdmin):
    """ Admin model for TaskBlackList """
