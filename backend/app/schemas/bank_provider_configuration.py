import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class BankProviderConfigurationUpsert(BaseModel):
    """Credentials accepted only on write; no read schema contains secrets."""

    client_id: str = Field(min_length=1, max_length=500)
    client_secret: SecretStr = Field(min_length=1, max_length=2000)
    enabled: bool = True


class BankProviderConfigurationUpdate(BaseModel):
    client_id: str | None = Field(default=None, min_length=1, max_length=500)
    client_secret: SecretStr | None = Field(default=None, min_length=1, max_length=2000)
    enabled: bool | None = None


class BankProviderConfigurationRead(BaseModel):
    id: uuid.UUID
    provider: str
    enabled: bool
    has_credentials: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
