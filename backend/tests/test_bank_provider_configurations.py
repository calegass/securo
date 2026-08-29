from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.crypto import decrypt_json, encrypt_json
from app.models.bank_provider_configuration import BankProviderConfiguration
from app.providers.base import ConnectTokenData
from app.services.connection_service import create_connect_token


@pytest.mark.asyncio
async def test_pluggy_configuration_is_private_and_encrypted(client: AsyncClient, auth_headers, session, test_user):
    response = await client.put(
        "/api/bank-provider-configurations/pluggy",
        headers=auth_headers,
        json={"client_id": "client-a", "client_secret": "secret-a"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "pluggy"
    assert body["has_credentials"] is True
    assert "client_id" not in body
    assert "client_secret" not in body

    configuration = await session.scalar(
        select(BankProviderConfiguration).where(BankProviderConfiguration.user_id == test_user.id)
    )
    assert configuration is not None
    assert "secret-a" not in configuration.credentials_encrypted
    assert decrypt_json(configuration.credentials_encrypted) == {
        "client_id": "client-a",
        "client_secret": "secret-a",
    }


@pytest.mark.asyncio
async def test_personal_pluggy_configuration_is_used_for_connect_token(session, test_user):
    configuration = BankProviderConfiguration(
        user_id=test_user.id,
        provider="pluggy",
        credentials_encrypted=encrypt_json({"client_id": "client-a", "client_secret": "secret-a"}),
    )
    session.add(configuration)
    await session.commit()

    provider = AsyncMock()
    provider.create_connect_token = AsyncMock(return_value=ConnectTokenData(access_token="token-a"))
    with patch("app.services.connection_service.get_provider", return_value=provider) as get_provider:
        result = await create_connect_token("pluggy", test_user.id, session=session)

    assert result == {"access_token": "token-a"}
    assert get_provider.call_args.kwargs["configuration"] == {
        "client_id": "client-a",
        "client_secret": "secret-a",
    }


@pytest.mark.asyncio
async def test_configurations_are_not_visible_to_other_users(client: AsyncClient, auth_headers, viewer_auth_headers):
    response = await client.put(
        "/api/bank-provider-configurations/pluggy",
        headers=auth_headers,
        json={"client_id": "client-a", "client_secret": "secret-a"},
    )
    assert response.status_code == 200

    other = await client.get("/api/bank-provider-configurations", headers=viewer_auth_headers)
    assert other.status_code == 200
    assert other.json() == []
