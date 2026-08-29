from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.bank_provider_configuration import (
    BankProviderConfigurationRead,
    BankProviderConfigurationUpdate,
    BankProviderConfigurationUpsert,
)
from app.services import bank_provider_configuration_service as configuration_service


router = APIRouter(prefix="/api/bank-provider-configurations", tags=["bank-provider-configurations"])


@router.get("", response_model=list[BankProviderConfigurationRead])
async def list_configurations(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await configuration_service.list_configurations(session, user.id)


@router.put("/{provider}", response_model=BankProviderConfigurationRead)
async def save_configuration(
    provider: str,
    data: BankProviderConfigurationUpsert,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await configuration_service.upsert_configuration(session, user.id, provider, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{provider}", response_model=BankProviderConfigurationRead)
async def update_configuration(
    provider: str,
    data: BankProviderConfigurationUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        configuration = await configuration_service.update_configuration(session, user.id, provider, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if configuration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider configuration not found")
    return configuration


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    provider: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        deleted = await configuration_service.delete_configuration(session, user.id, provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider configuration not found")
