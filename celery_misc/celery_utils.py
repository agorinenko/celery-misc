import logging
import pprint
from functools import wraps, partial
from typing import Callable

from celery import Task
from django import db
from django.conf import settings

from celery_misc import errors

logger = logging.getLogger(__name__)


def cleanup_db_connections(func):
    """ Check connections """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if settings.CELERY_EAGER:
            return func(*args, **kwargs)

        check_connections()

        try:
            return func(*args, **kwargs)
        except (db.OperationalError, db.InterfaceError) as exc:
            logger.exception(exc)
            db.close_old_connections()
            try:
                return func(*args, **kwargs)
            except (db.OperationalError, db.InterfaceError):
                raise
        finally:
            db.close_old_connections()

    return wrapper


def check_connections():
    """
    Проверка соединений с Django
    """
    for conn in db.connections.all():
        try:
            cur = conn.cursor()
            _ = cur.execute('SELECT 1')
        except (db.OperationalError, db.InterfaceError):
            conn.close()


@cleanup_db_connections
def common_celery_task(*args,
                       retry_if_error: bool | None = True,
                       suppress_error: bool | None = False,
                       before_send: Callable | None = None,
                       **kwargs):
    task = None
    if len(args) < 1:
        raise ValueError('Неверное использование common_celery_task. Не указана функция для выполнения.')
    args = list(args)
    if isinstance(args[0], Task):
        if len(args) < 2:
            raise ValueError('Неверное использование common_celery_task. Не указана функция для выполнения.')
        task = args.pop(0)
        task_function = args.pop(0)
    else:
        task_function = args.pop(0)

    if not callable(task_function):
        raise ValueError('Неверное использование common_celery_task. Функция для выполнения не может быть вызвана.')

    task_name = task.name if task else ''
    logger.debug("================ START TASK %s ================\nargs: %s\nkwargs: %s", task_name,
                 pprint.pformat(args), pprint.pformat(kwargs))
    try:
        if task:
            if before_send:
                before_send(task, *args, **kwargs)
            return task_function(task, *args, **kwargs)

        if before_send:
            before_send(*args, **kwargs)
        return task_function(*args, **kwargs)
    except errors.SoftStop as ex:
        message = str(ex)
        if message:
            logger.info(message)
    except Exception as ex:  # pylint: disable=broad-except
        logger.error(f'Возникла ошибка при выполнении задачи %s.', task_name)
        logger.exception(ex)
        if retry_if_error:
            raise task.retry(exc=ex)

        if not suppress_error:
            raise ex

    finally:
        logger.debug("================ END TASK %s ================", task_name)


safety_celery_task = partial(common_celery_task, retry_if_error=False, suppress_error=True)
