import importlib
import inspect
import threading
from typing import Any


class SingletonMeta(type):
    """ Потоко безопасный мета класс для Singleton """

    _instances: dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


def load_class(fqdn: str, base_class: type | None = None):
    """
    Динамическая загрузка класса по его FQDN
    fqdn: Полное имя класса (например, 'celery_misc.transactional_outbox.strategies.DummyBlockBatchStrategy')
    base_class: если задан, загруженный класс обязан быть его подклассом
    Returns:
        Загруженный класс
    """
    module_path, class_name = fqdn.rsplit('.', 1)
    module = importlib.import_module(module_path)
    loaded = getattr(module, class_name)

    if base_class is not None and not (inspect.isclass(loaded) and issubclass(loaded, base_class)):
        raise TypeError(f'Класс "{fqdn}" не является подклассом "{base_class.__module__}.{base_class.__qualname__}".')

    return loaded
