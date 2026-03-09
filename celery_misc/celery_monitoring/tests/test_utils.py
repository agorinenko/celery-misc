import pytest

from celery_misc.celery_monitoring import monitoring_utils

pytestmark = pytest.mark.django_db


def test_is_monitoring():
    """ Базовый сценарий """
    task_name = 'celery_misc.celery_monitoring.tasks.delete_running_log_task'
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)
    monitoring_utils.TASK_REPOSITORY.register(task_name)
    monitoring_utils.TASK_REPOSITORY.register(task_name)
    assert monitoring_utils.TASK_REPOSITORY.get_task_record(task_name)
    # После регистрации задача доступна для мониторинга
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)

    monitoring_utils.TASK_REPOSITORY.add_to_white_list(task_name)
    monitoring_utils.TASK_REPOSITORY.add_to_black_list(task_name)

    status = monitoring_utils.TASK_REPOSITORY.remove_register(task_name)
    assert status

    status = monitoring_utils.TASK_REPOSITORY.remove_register(task_name)
    assert not status


def test_is_monitoring__white_list():
    """ Белый список """
    task_name = 'celery_misc.celery_monitoring.tasks.delete_running_log_task'
    # По умолчанию для мониторинга доступны все задачи
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)
    monitoring_utils.TASK_REPOSITORY.add_to_white_list('web_app.some_task')
    # Задача еще не зарегистрирована, поэтому доступна для мониторинга даже если белый список не пуст
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)
    monitoring_utils.TASK_REPOSITORY.register(task_name)
    # Задача уже зарегистрирована, но не добавлена в белый список, который не пуст
    assert not monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)
    # Добавляем в белый список
    monitoring_utils.TASK_REPOSITORY.add_to_white_list(task_name)
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)
    # После включения в черный список, задача не доступна для мониторинга
    monitoring_utils.TASK_REPOSITORY.add_to_black_list(task_name)
    assert not monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)
    # Проверка обратных функций
    monitoring_utils.TASK_REPOSITORY.remove_from_black_list(task_name)
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)

    status = monitoring_utils.TASK_REPOSITORY.remove_from_white_list(task_name)
    assert status
    # В белом списке есть другая задача
    assert not monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)

    status = monitoring_utils.TASK_REPOSITORY.remove_from_white_list(task_name)
    assert not status

    monitoring_utils.TASK_REPOSITORY.remove_register(task_name)
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)


def test_is_monitoring__black_list():
    """ Черный список """
    task_name = 'celery_misc.celery_monitoring.tasks.delete_running_log_task'
    monitoring_utils.TASK_REPOSITORY.add_to_black_list(task_name)
    assert not monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)
    # Черный список имеет приоритет
    monitoring_utils.TASK_REPOSITORY.add_to_white_list(task_name)
    assert not monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)

    status = monitoring_utils.TASK_REPOSITORY.remove_from_black_list(task_name)
    assert status
    assert monitoring_utils.TASK_REPOSITORY.is_monitoring(task_name)

    status = monitoring_utils.TASK_REPOSITORY.remove_from_black_list(task_name)
    assert not status
