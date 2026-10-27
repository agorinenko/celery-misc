import abc
import logging

from django.db import transaction
from django.db.models import QuerySet, Q
from django.utils import timezone

from celery_misc.transactional_outbox import models, enums

logger = logging.getLogger(__name__)


def get_pending_outbox_messages(event_ids: list[int] = None):
    """ Получение QuerySet сообщений, ожидающих отправку """
    pending_query_set = models.OutboxMessage.objects.filter(
        ~Q(Q(status=enums.EventStatuses.SENT) | Q(status=enums.EventStatuses.EXPIRED))  # Не отправлено или устарело
    )

    if event_ids:
        pending_query_set = pending_query_set.filter(id__in=event_ids)

    return pending_query_set


class BaseSendEventsStrategy(abc.ABC):
    def __init__(self, batch_size: int | None = None):
        self.batch_size = batch_size

    @abc.abstractmethod
    def publish_message(self, message: models.OutboxMessage):
        """ Отправка уведомления во внешнюю систему, например в kafka или rabbit """
        raise NotImplementedError(
            'Требуется реализовать функцию отправки сообщения во внешнюю систему publish_message.')

    def process_base_query(self, query_set: QuerySet[models.OutboxMessage]):
        """ Дополнительная обработка запроса """
        return query_set

    def send_events(self, event_ids: list[int]|None = None, external_filter: Q | None = None) -> list[int]:
        """
        Отправка уведомлений во внешнюю систему, например в kafka или rabbit
        :param external_filter: дополнительный фильтр
        :param event_ids: список ID событий для обработки
        :return: список ID сообщений с неудавшейся отправкой
        Пояснения.
        1. Зачем select_for_update(skip_locked=True) в общем запросе?
            Что делает select_for_update?
            Блокирует выбранные строки до конца транзакции, чтобы другие транзакции не могли их изменить.
            Что делает skip_locked=True?
            Пропускает уже заблокированные строки и возвращает только те, которые свободны.
        2. Почему используется batch_size?
            1. Защита памяти
            2. Время выполнения транзакции:
            Чем больше записей в транзакции, тем дольше она выполняется
            Долгие транзакции увеличивают риск конфликтов и deadlock'ов(за счет отправку во внешнюю систему)
            БД держит блокировки до конца транзакции
            3. Равномерное распределение нагрузки:
            Каждый воркер берет небольшую порцию и быстро освобождает блокировки
            Другие воркеры могут сразу начать обрабатывать следующие порции
        """
        pending_query_set = get_pending_outbox_messages(event_ids=event_ids).order_by('created_at', 'id')

        if external_filter:
            pending_query_set = pending_query_set.filter(external_filter)

        if self.batch_size and not event_ids:
            pending_query_set = pending_query_set[:self.batch_size]

        pending_query_set = self.process_base_query(pending_query_set)
        error_messages = []
        for message in pending_query_set:
            status = self.process_one_message(message)
            if not status:
                error_messages.append(message.id)

        return error_messages

    def process_one_message(self, message: models.OutboxMessage) -> bool:
        """ Обработка одного сообщения """
        try:
            self.publish_message(message)  # Возможна долгая работа
            message.status = enums.EventStatuses.SENT
            message.sent_at = timezone.now()
            message.save()
            return True
        except Exception as ex:
            message.status = enums.EventStatuses.FAILED
            message.error = str(ex)
            message.save()

            logger.error('Произошла ошибка при отправки сообщения во внешнюю систему. ID#%s', message.id)
            logger.exception(ex)
            return False


class BlockBatchStrategy(BaseSendEventsStrategy, abc.ABC):
    """
    Стратегия блокирования всего пакета сообщений.
    В этом случае не нужно дополнительно проверять статус сообщений и открывать отдельные транзакции,
    так как создается одна длительная транзакция. Batch_size желательно уменьшить, чтобы сократить время общей блокировки.
    """

    def send_events(self, *args, **kwargs) -> list[int]:
        with transaction.atomic():
            return super().send_events(*args, **kwargs)

    def process_base_query(self, query_set: QuerySet[models.OutboxMessage]):
        """ Блокировка запроса
        Зачем нужна select_for_update(skip_locked=True) в общем запросе?
            Цель: распределение работы между конкурентными воркерами
            FOR UPDATE — блокирует выбранные строки, чтобы другие воркеры их не взяли
            SKIP LOCKED — позволяет воркерам работать параллельно, не ожидая друг друга
            [:batch_size] — ограничивает порцию, чтобы быстро освобождать блокировки
            Результат: несколько воркеров могут одновременно обрабатывать РАЗНЫЕ сообщения из очереди.
        """
        return query_set.select_for_update(skip_locked=True)


class CheckStatusStrategy(BaseSendEventsStrategy, abc.ABC):
    """
    Стратегия без долгих блокировок: сообщение захватывается атомарным
    условным UPDATE (PENDING/FAILED -> SENDING), публикация выполняется вне
    транзакции, финальный статус (SENT/FAILED) пишется отдельным коротким UPDATE.

    Защита от двойной отправки обеспечивается условием захвата: перевести строку
    в SENDING может только один воркер (rowcount == 1). «Зависшие» в SENDING
    сообщения (падение воркера между захватом и финализацией) возвращает в PENDING
    периодическая задача requeue_stale_events.
    """

    def process_one_message(self, message: models.OutboxMessage) -> bool:
        """ Атомарный захват сообщения без долгой блокировки """
        claimed = (
            models.OutboxMessage.objects
            .filter(id=message.id, status__in=[enums.EventStatuses.PENDING, enums.EventStatuses.FAILED])
            .update(status=enums.EventStatuses.SENDING, updated_at=timezone.now())
        )
        if not claimed:
            # Сообщение уже отправлено или захвачено другим воркером
            return True

        try:
            # Внешний вызов — строка больше не заблокирована
            self.publish_message(message)

            models.OutboxMessage.objects.filter(id=message.id).update(
                status=enums.EventStatuses.SENT,
                sent_at=timezone.now(),
                updated_at=timezone.now(),
                error=None
            )
            return True
        except Exception as ex:
            models.OutboxMessage.objects.filter(id=message.id).update(
                status=enums.EventStatuses.FAILED,
                error=str(ex),
                updated_at=timezone.now()
            )

            logger.error('Произошла ошибка при отправки сообщения во внешнюю систему. ID#%s', message.id)
            logger.exception(ex)
            return False


class DummyBlockBatchStrategy(BlockBatchStrategy):
    def publish_message(self, message: models.OutboxMessage):
        logger.info('Отправка сообщения ID#%s.', message.id)


class DummyCheckStatusStrategy(CheckStatusStrategy):
    def publish_message(self, message: models.OutboxMessage):
        logger.info('Отправка сообщения ID#%s.', message.id)
