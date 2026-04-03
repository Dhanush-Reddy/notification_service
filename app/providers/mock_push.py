import logging
import random

from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class MockPushProvider(BaseProvider):
    FAILURE_RATE = 0.05

    async def send(self, notification) -> bool:
        # TODO: replace with FCM/APNs in production
        if random.random() < self.FAILURE_RATE:
            raise RuntimeError("MockPushProvider: simulated transient failure")

        logger.info(
            "[PUSH] user=%s body_preview=%r",
            notification.user_id,
            notification.body[:60],
        )
        return True
