from collections.abc import Generator
from contextlib import contextmanager, ExitStack
from typing import Callable

from django.db.models import Model


class DisableSignal:
    """
    Временное отключение сигналов Django
    """

    def __init__(self, signal,
                 receiver: Callable,
                 sender: type[Model] | str | None = None,
                 dispatch_uid: str | None = None,
                 weak: bool | None = True):
        self.signal = signal
        self.receiver = receiver
        self.sender = sender
        self.dispatch_uid = dispatch_uid
        if weak is None:
            signal_info = self.get_signal_info()
            if not signal_info:
                raise ValueError('Явно укажите параметр weak. Сигнал не найден.')
            weak = signal_info[2]
        self.weak = weak

    def __enter__(self):
        self.signal.disconnect(receiver=self.receiver, sender=self.sender, dispatch_uid=self.dispatch_uid)

    def __exit__(self, exc_type, exc_value, traceback):
        self.signal.connect(receiver=self.receiver, sender=self.sender, dispatch_uid=self.dispatch_uid, weak=self.weak)

    def get_signal_id(self):
        if self.dispatch_uid:
            lookup_key = (self.dispatch_uid, _make_id(self.sender))
        else:
            lookup_key = (_make_id(self.receiver), _make_id(self.sender))

        return lookup_key

    def get_signal_info(self):
        lookup_key = self.get_signal_id()
        for receiver in self.signal.receivers:
            if lookup_key == receiver[0]:
                return receiver
        return None


SignalConfigType = DisableSignal | tuple[list, dict]


@contextmanager
def disable_signals(signals_config: list[SignalConfigType]) -> Generator[None, None, None]:
    signal_managers = []
    for signal_config in signals_config:
        if isinstance(signal_config, DisableSignal):
            signal_managers.append(signal_config)
        else:
            signal_args, signal_kwargs = signal_config
            signal_managers.append(DisableSignal(*signal_args, **signal_kwargs))

    with ExitStack() as stack:
        for manager in signal_managers:
            stack.enter_context(manager)

        yield


def _make_id(target):
    if hasattr(target, "__func__"):
        return (id(target.__self__), id(target.__func__))
    return id(target)


NONE_ID = _make_id(None)
