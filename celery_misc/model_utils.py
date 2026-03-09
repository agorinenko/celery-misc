import logging
import time
from typing import Callable

from django.db.models import Q

logger = logging.getLogger(__name__)


def batch_processing(queryset, query: Q, action: Callable,
                     batch_size: int | None = 2000,
                     batch_interval: float | None = 0.1,
                     order_by_fields: list[str] = None,
                     terminator: Callable | None = None,
                     max_empty_iter: int | None = None,
                     need_select_for_update: bool | None = False, **kwargs):
    """ Массовые операции """
    queryset = queryset.model.objects.filter(query)
    if order_by_fields:
        queryset = queryset.order_by(*order_by_fields)

    current_no = queryset.count()
    total_count = 0
    empty_iter = 0
    terminator_exists = callable(terminator)
    while current_no:
        # Удаляем порцию данных

        flat_queryset = queryset.values_list('id', flat=True)[:batch_size]
        if need_select_for_update:
            flat_queryset = flat_queryset.select_for_update()

        item_ids = list(flat_queryset)
        processed_count = action(queryset, item_ids, **kwargs)
        if max_empty_iter and max_empty_iter > 0 and processed_count == 0:
            empty_iter += 1
            if empty_iter >= max_empty_iter:
                logger.debug('The maximum number %s of iterations with an empty result has been reached.',
                             max_empty_iter)
                return total_count

        total_count += processed_count
        logger.debug('Processing %s items. Batch size %s, total count %s.', processed_count, batch_size, total_count)
        # Обновляем queryset и количество current_no объектов для удаления
        queryset = queryset.model.objects.filter(query)
        if order_by_fields:
            queryset = queryset.order_by(*order_by_fields)
        current_no = queryset.count()

        if current_no > 0 and terminator_exists and terminator():
            logger.debug('Terminate.')
            return total_count

        if batch_interval > 0:
            time.sleep(batch_interval)

    return total_count


def _delete_queryset(queryset, item_ids: list):
    deleted, _ = queryset.model.objects.filter(id__in=item_ids).delete()
    return deleted


def batch_delete(queryset, query: Q,
                 batch_size: int | None = 2000,
                 batch_interval: float | None = 0.1,
                 order_by_fields: list[str] = None,
                 terminator: Callable | None = None):
    """ Массовое удаление """
    return batch_processing(queryset, query, _delete_queryset, batch_size=batch_size,
                            batch_interval=batch_interval, order_by_fields=order_by_fields,
                            terminator=terminator)
