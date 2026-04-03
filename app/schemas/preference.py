from pydantic import BaseModel, field_validator

VALID_CHANNELS = {"email", "sms", "push"}


class PreferenceUpdate(BaseModel):
    channel: str
    is_enabled: bool

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if v not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {VALID_CHANNELS}")
        return v


class PreferenceResponse(BaseModel):
    channel: str
    is_enabled: bool

    model_config = {"from_attributes": True}
