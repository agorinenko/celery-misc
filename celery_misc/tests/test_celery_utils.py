import logging

import pytest
from django.db import InterfaceError, OperationalError
from django.test.utils import override_settings

from celery_misc import celery_utils

LOGGER_NAME = 'celery_misc.celery_utils'


class FakeCursor:
    """ Курсор, падающий при выполнении запроса """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql):
        raise OperationalError('server closed the connection unexpectedly')


class HealthyCursor(FakeCursor):
    """ Работоспособный курсор """

    def execute(self, sql):
        return None


class FakePool:
    """ Пул соединений psycopg_pool """

    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def check(self):
        self.calls += 1
        if self.error:
            raise self.error


class FakeConnection:
    """ Соединение с БД """

    def __init__(self, cursor_class=FakeCursor, pool=None, alias='default'):
        self.cursor_class = cursor_class
        self.pool = pool
        self.alias = alias
        self.closed = False

    def cursor(self):
        return self.cursor_class()

    def close(self):
        self.closed = True


@pytest.fixture
def no_db(mocker):
    """ Исключить обращения к реальным соединениям с БД """
    mocker.patch.object(celery_utils, 'check_connections')
    mocker.patch.object(celery_utils.db, 'close_old_connections')


@pytest.fixture
def log(caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    return caplog


def test_cleanup_db_connections__retry_success(no_db, log):
    """ Ошибка соединения с БД восстановлена повтором: ERROR не пишется """
    calls = 0

    def func():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OperationalError('server closed the connection unexpectedly')
        return 'ok'

    with override_settings(CELERY_EAGER=False):
        assert celery_utils.cleanup_db_connections(func)() == 'ok'

    assert calls == 2
    # Соединения проверяются и перед первой попыткой, и перед повтором
    assert celery_utils.check_connections.call_count == 2
    assert not [record for record in log.records if record.levelno == logging.ERROR]
    assert [record for record in log.records
            if record.levelno == logging.WARNING and 'Повтор операции' in record.getMessage()]


def test_cleanup_db_connections__retry_failed(no_db, log):
    """ Повтор не помог: пишется одна ERROR-запись с трейсбеком """
    calls = 0

    def func():
        nonlocal calls
        calls += 1
        raise InterfaceError('connection is closed')

    with override_settings(CELERY_EAGER=False):
        with pytest.raises(InterfaceError):
            celery_utils.cleanup_db_connections(func)()

    assert calls == 2
    errors = [record for record in log.records if record.levelno == logging.ERROR]
    assert len(errors) == 1
    assert errors[0].exc_info


def test_cleanup_db_connections__eager(no_db):
    """ В eager-режиме проверки и повтора нет """
    calls = 0

    def func():
        nonlocal calls
        calls += 1
        raise OperationalError('server closed the connection unexpectedly')

    with override_settings(CELERY_EAGER=True):
        with pytest.raises(OperationalError):
            celery_utils.cleanup_db_connections(func)()

    assert calls == 1
    celery_utils.check_connections.assert_not_called()
    celery_utils.db.close_old_connections.assert_not_called()


def test_check_connections__broken_connection(mocker, log):
    """ Неработоспособное соединение закрывается, пул проверяется """
    pool = FakePool()
    conn = FakeConnection(pool=pool)
    mocker.patch.object(celery_utils.db.connections, 'all', return_value=[conn])

    celery_utils.check_connections()

    assert conn.closed
    assert pool.calls == 1
    assert [record for record in log.records
            if record.levelno == logging.WARNING and conn.alias in record.getMessage()]


def test_check_connections__healthy_connection(mocker, log):
    """ Работоспособное соединение не закрывается, пул не проверяется """
    pool = FakePool()
    conn = FakeConnection(cursor_class=HealthyCursor, pool=pool)
    mocker.patch.object(celery_utils.db.connections, 'all', return_value=[conn])

    celery_utils.check_connections()

    assert not conn.closed
    assert pool.calls == 0
    assert not [record for record in log.records if record.levelno >= logging.WARNING]


@pytest.mark.parametrize('pool', [
    None,
    object(),
    type('PoolWithoutCallableCheck', (), {'check': 42})(),
])
def test_check_connection_pool__no_check(pool):
    """ Соединения без пула и пул без вызываемого check - no-op """
    celery_utils._check_connection_pool(FakeConnection(pool=pool))


def test_check_connection_pool__no_pool_attribute():
    """ У соединения может вообще не быть атрибута pool """
    celery_utils._check_connection_pool(object())


def test_check_connection_pool__calls_pool_check():
    """ Пул проверяется через публичный метод check """
    pool = FakePool()

    celery_utils._check_connection_pool(FakeConnection(pool=pool))

    assert pool.calls == 1


def test_check_connection_pool__error_is_logged(log):
    """ Ошибка проверки пула не пробрасывается, а логируется """
    pool = FakePool(error=RuntimeError('boom'))

    celery_utils._check_connection_pool(FakeConnection(pool=pool))

    assert pool.calls == 1
    assert [record for record in log.records if record.levelno == logging.WARNING]


@pytest.mark.parametrize('exc, expected', [
    (OperationalError('server closed the connection unexpectedly'), True),
    (InterfaceError('connection is closed'), True),
    (ValueError('bad'), False),
])
def test_is_db_error(exc, expected):
    assert celery_utils._is_db_error(exc) is expected


def test_common_celery_task__db_error(no_db, log):
    """ Ошибка БД логируется как WARNING, итог с учётом повтора - в cleanup_db_connections """
    def func():
        raise OperationalError('server closed the connection unexpectedly')

    with override_settings(CELERY_EAGER=True):
        with pytest.raises(OperationalError):
            celery_utils.common_celery_task(func)

    assert not [record for record in log.records if record.levelno == logging.ERROR]
    assert [record for record in log.records
            if record.levelno == logging.WARNING and 'Ошибка БД' in record.getMessage()]


def test_common_celery_task__other_error(no_db, log):
    """ Прочие исключения логируются одной ERROR-записью с трейсбеком """
    def func():
        raise ValueError('bad')

    with override_settings(CELERY_EAGER=True):
        with pytest.raises(ValueError):
            celery_utils.common_celery_task(func)

    errors = [record for record in log.records if record.levelno == logging.ERROR]
    assert len(errors) == 1
    assert errors[0].exc_info
    assert 'Возникла ошибка при выполнении задачи' in errors[0].getMessage()


def test_common_celery_task__suppress_error(no_db, log):
    """ При suppress_error=True исключение не пробрасывается """
    def func():
        raise ValueError('bad')

    with override_settings(CELERY_EAGER=True):
        assert celery_utils.common_celery_task(func, suppress_error=True) is None

    assert [record for record in log.records if record.levelno == logging.ERROR]
