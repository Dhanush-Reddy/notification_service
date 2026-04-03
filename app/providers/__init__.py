from app.providers.base import BaseProvider
from app.providers.mock_email import MockEmailProvider
from app.providers.mock_sms import MockSMSProvider
from app.providers.mock_push import MockPushProvider

_PROVIDERS: dict[str, BaseProvider] = {
    "email": MockEmailProvider(),
    "sms": MockSMSProvider(),
    "push": MockPushProvider(),
}


def get_provider(channel: str) -> BaseProvider:
    provider = _PROVIDERS.get(channel)
    if provider is None:
        raise ValueError(f"No provider registered for channel: {channel!r}")
    return provider
