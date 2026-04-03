import logging
import random

from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class MockSMSProvider(BaseProvider):
    FAILURE_RATE = 0.05

    async def send(self, notification) -> bool:
        # TODO: replace with Twilio/SNS in production
        if random.random() < self.FAILURE_RATE:
            raise RuntimeError("MockSMSProvider: simulated transient failure")

        logger.info(
            "[SMS] user=%s body_preview=%r",
            notification.user_id,
            notification.body[:60],
        )
        return True
