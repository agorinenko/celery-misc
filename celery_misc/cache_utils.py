import logging
import abc
from typing import Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


class BaseCache(abc.ABC):
    """
    Класс, декларирующий общие методы работы с кешем
    """

    def __init__(self, expired_timeout: float | None = 300):
        """
        expired_timeout - время устаревания кэша по умолчанию, в секундах.
        По умолчанию 300 секунд (5 минут). Вы можете установить expired_timeout в None, тогда кэш никогда не устареет.
        Если указать 0, все ключи будут сразу устаревать (таким образом, можно заставить «не кэшировать»).
        """
        self.expired_timeout = expired_timeout

    @abc.abstractmethod
    def set_value(self, cache_key: str, cache_value: Any) -> None:
        """ Установка значения """
        raise NotImplementedError('set_value')

    @abc.abstractmethod
    def get_value(self, cache_key: str) -> Any | None:
        """ Получение значения """
        raise NotImplementedError('get_value')

    @abc.abstractmethod
    def clear_cache(self) -> None:
        """ Очистка кеша """
        raise NotImplementedError('clear_cache')

    @abc.abstractmethod
    def delete_pattern(self, pattern: str) -> int | None:
        """ Удаление ключей по шаблону (только для Redis бекенда) """
        raise NotImplementedError('delete_pattern')


class DjangoCache(BaseCache):
    """
    Класс, реализующий хранение в кеше Django
    (с использованием бекенда, определенной в конфигурации, переменная CACHES)
    """

    def set_value(self, cache_key: str, cache_value: Any) -> None:
        logger.debug('Set value for key "%s" in DjangoCache.', cache_key)
        cache.set(cache_key, cache_value, timeout=self.expired_timeout)

    def get_value(self, cache_key: str) -> Any | None:
        if cache.has_key(cache_key):
            logger.debug('Get value for key "%s" from DjangoCache.', cache_key)
            return cache.get(cache_key)

        logger.debug('Key "%s" not found in DjangoCache.', cache_key)
        return None

    def clear_cache(self, key: str | None = None) -> None:
        if key:
            if cache.has_key(key):
                logger.debug('Delete key "%s" from DjangoCache.', key)
                cache.delete(key)
            else:
                logger.debug('Key "%s" not found in DjangoCache.', key)
        else:
            cache.clear()
            logger.debug('Clear DjangoCache.')

    def delete_pattern(self, pattern: str) -> int | None:
        """ Удаление ключей по шаблону (только для Redis бекенда) """
        deleted_count = 0

        # Проверяем, используем ли мы Redis бекенд
        if hasattr(cache, 'delete_pattern'):
            # Для django-redis
            deleted_count = cache.delete_pattern(pattern)
            logger.debug('Deleted %d keys with pattern "%s" from DjangoCache.', deleted_count, pattern)
        elif hasattr(cache, 'keys'):
            # получить все ключи и удалить совпадающие
            all_keys = cache.keys('*')
            keys_to_delete = [k for k in all_keys if pattern.replace('*', '') in k]
            if keys_to_delete:
                deleted_count = cache.delete_many(keys_to_delete)
                logger.debug('Deleted %d keys matching pattern "%s" from DjangoCache.', deleted_count, pattern)
        else:
            # Для бекендов без поддержки паттернов
            logger.warning('Current cache backend does not support pattern deletion. Use clear_cache() instead.')

        return deleted_count
