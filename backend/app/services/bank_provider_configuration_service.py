"""Persistence and safe resolution of user-owned provider configurations."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_json, encrypt_json
from app.models.bank_provider_configuration import BankProviderConfiguration
from app.models.bank_connection import BankConnection
from app.schemas.bank_provider_configuration import (
    BankProviderConfigurationUpdate,
    BankProviderConfigurationUpsert,
)


SUPPORTED_USER_CONFIG_PROVIDERS = frozenset({"pluggy"})


def _validate_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_USER_CONFIG_PROVIDERS:
        raise ValueError(f"Provider '{provider}' does not support user configuration")
    return normalized


async def list_configurations(
    session: AsyncSession, user_id: uuid.UUID
) -> list[BankProviderConfiguration]:
    result = await session.execute(
        select(BankProviderConfiguration)
        .where(BankProviderConfiguration.user_id == user_id)
        .order_by(BankProviderConfiguration.provider)
    )
    return list(result.scalars().all())


async def get_configuration(
    session: AsyncSession, user_id: uuid.UUID, provider: str
) -> BankProviderConfiguration | None:
    provider = _validate_provider(provider)
    return await session.scalar(
        select(BankProviderConfiguration).where(
            BankProviderConfiguration.user_id == user_id,
            BankProviderConfiguration.provider == provider,
        )
    )


async def upsert_configuration(
    session: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    data: BankProviderConfigurationUpsert,
) -> BankProviderConfiguration:
    provider = _validate_provider(provider)
    configuration = await get_configuration(session, user_id, provider)
    encrypted = encrypt_json(
        {
            "client_id": data.client_id.strip(),
            "client_secret": data.client_secret.get_secret_value(),
        }
    )
    if configuration is None:
        configuration = BankProviderConfiguration(
            user_id=user_id,
            provider=provider,
            credentials_encrypted=encrypted,
            enabled=data.enabled,
        )
        session.add(configuration)
    else:
        configuration.credentials_encrypted = encrypted
        configuration.enabled = data.enabled
    await session.commit()
    await session.refresh(configuration)
    return configuration


async def update_configuration(
    session: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    data: BankProviderConfigurationUpdate,
) -> BankProviderConfiguration | None:
    configuration = await get_configuration(session, user_id, provider)
    if configuration is None:
        return None

    updates = data.model_dump(exclude_unset=True)
    if "client_id" in updates or "client_secret" in updates:
        current = decrypt_json(configuration.credentials_encrypted)
        if not current:
            raise ValueError("Stored provider credentials are unreadable; replace both values")
        client_id = updates.get("client_id", current.get("client_id"))
        secret = updates.get("client_secret")
        client_secret = secret.get_secret_value() if secret is not None else current.get("client_secret")
        if not isinstance(client_id, str) or not client_id.strip() or not isinstance(client_secret, str) or not client_secret:
            raise ValueError("Both client ID and client secret are required")
        configuration.credentials_encrypted = encrypt_json(
            {"client_id": client_id.strip(), "client_secret": client_secret}
        )
    if "enabled" in updates:
        configuration.enabled = updates["enabled"]
    await session.commit()
    await session.refresh(configuration)
    return configuration


async def delete_configuration(
    session: AsyncSession, user_id: uuid.UUID, provider: str
) -> bool:
    configuration = await get_configuration(session, user_id, provider)
    if configuration is None:
        return False
    connection_exists = await session.scalar(
        select(BankConnection.id)
        .where(BankConnection.provider_configuration_id == configuration.id)
        .limit(1)
    )
    if connection_exists is not None:
        raise ValueError("Disconnect or move the provider connections before deleting this configuration")
    await session.delete(configuration)
    await session.commit()
    return True


def decrypt_configuration(configuration: BankProviderConfiguration) -> dict[str, str]:
    """Decrypt one enabled configuration for server-side provider construction."""
    if not configuration.enabled:
        raise ValueError(f"Provider '{configuration.provider}' is disabled")
    data = decrypt_json(configuration.credentials_encrypted)
    client_id = data.get("client_id") if data else None
    client_secret = data.get("client_secret") if data else None
    if not isinstance(client_id, str) or not isinstance(client_secret, str) or not client_id or not client_secret:
        raise ValueError(f"Provider '{configuration.provider}' credentials are unreadable")
    return {"client_id": client_id, "client_secret": client_secret}
