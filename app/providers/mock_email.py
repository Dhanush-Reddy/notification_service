import logging
import random

from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class MockEmailProvider(BaseProvider):
    # simulate ~5% failure rate so retry logic actually gets exercised
    FAILURE_RATE = 0.05

    async def send(self, notification) -> bool:
        # TODO: replace with real SendGrid/SES call in production
        if random.random() < self.FAILURE_RATE:
            raise RuntimeError("MockEmailProvider: simulated transient failure")

        logger.info(
            "[EMAIL] user=%s subject=%r body_preview=%r",
            notification.user_id,
            notification.subject,
            notification.body[:60],
        )
        return True
