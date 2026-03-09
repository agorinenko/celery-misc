# pylint: disable=all
from django.apps import AppConfig


class WebAppConfig(AppConfig):
    """ Основное веб-приложение """

    name = "web_app"
    verbose_name = "Веб приложение"

    def ready(self):
        try:
            from web_app import tasks
        except ImportError as ex:
            pass
