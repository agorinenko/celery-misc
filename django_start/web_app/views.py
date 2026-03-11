from celery_misc.transactional_outbox import models
from celery_misc.transactional_outbox.strategies import BlockBatchStrategy, CheckStatusStrategy


class DummyBlockBatchStrategy(BlockBatchStrategy):
    def publish_message(self, message: models.OutboxMessage):
        pass


class DummyCheckStatusStrategy(CheckStatusStrategy):
    def publish_message(self, message: models.OutboxMessage):
        pass