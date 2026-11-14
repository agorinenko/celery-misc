import logging
import pprint
from functools import wraps, partial
from typing import Callable

from celery import Task
from celery.utils.time import get_exponential_backoff_interval

try:
    from django import db
    from django.conf import settings

    WITH_DJANGO = True
except ImportError:
    WITH_DJANGO = False

from celery_misc import errors

logger = logging.getLogger(__name__)


def cleanup_db_connections(func):
    """ Check connections """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not WITH_DJANGO:
            return func(*args, **kwargs)

        if getattr(settings, 'CELERY_EAGER', False):
            return func(*args, **kwargs)

        check_connections()

        try:
            return func(*args, **kwargs)
        except (db.OperationalError, db.InterfaceError) as exc:
            logger.warning('Повтор операции на ошибку: %s', str(exc))
            db.close_old_connections()
            check_connections()
            try:
                return func(*args, **kwargs)
            except (db.OperationalError, db.InterfaceError) as exc2:
                logger.exception(exc2)
                raise
        finally:
            db.close_old_connections()

    return wrapper


def _check_connection_pool(conn):
    """
    Проверка свободных соединений пула psycopg_pool (Django >= 5.1).

    Пул проверяет все свободные соединения, битые выбрасывает и создаёт вместо них новые.
    Для соединений без пула и для psycopg_pool без метода check - ничего не делает.
    """
    try:
        pool = getattr(conn, 'pool', None)
        check = getattr(pool, 'check', None)
        if not callable(check):
            return
        check()
    except Exception:  # pylint: disable=broad-except
        logger.warning('Не удалось проверить пул соединений БД "%s".',
                       getattr(conn, 'alias', ''), exc_info=True)


def _is_db_error(exc) -> bool:
    """ Ошибка соединения с БД, которую обрабатывает cleanup_db_connections """
    return WITH_DJANGO and isinstance(exc, (db.OperationalError, db.InterfaceError))


def check_connections():
    """
    Проверка соединений с Django
    """
    if not WITH_DJANGO:
        return

    for conn in db.connections.all():
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
        except (db.OperationalError, db.InterfaceError) as exc:
            logger.warning('Соединение с БД "%s" неработоспособно и будет закрыто: %s', conn.alias, exc)
            conn.close()
            _check_connection_pool(conn)


@cleanup_db_connections
def common_celery_task(
        *args, retry_if_error: bool | None = True,
        suppress_error: bool | None = False,
        before_send: Callable | None = None,
        retry_backoff: int = 2,
        retry_backoff_max: int = 600,
        retry_jitter: bool = True,
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
        if _is_db_error(ex):
            # Итог с учётом повтора логирует cleanup_db_connections
            logger.warning('Ошибка БД при выполнении задачи %s: %s', task_name, str(ex))
        else:
            logger.exception('Возникла ошибка при выполнении задачи %s.', task_name)
        if retry_if_error and task and hasattr(task, 'retry'):
            countdown = get_exponential_backoff_interval(
                factor=retry_backoff, retries=task.request.retries,
                maximum=retry_backoff_max, full_jitter=retry_jitter,
            )
            raise task.retry(exc=ex, countdown=countdown)

        if not suppress_error:
            raise ex

    finally:
        logger.debug("================ END TASK %s ================", task_name)


safety_celery_task = partial(common_celery_task, retry_if_error=False, suppress_error=True)
