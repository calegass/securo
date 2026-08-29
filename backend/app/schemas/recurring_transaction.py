import uuid
from datetime import date as _Date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

WeekendAdjustment = Literal["none", "previous_friday", "next_monday"]


class RecurringTransactionCreate(BaseModel):
    description: str
    notes: Optional[str] = None
    amount: Decimal
    currency: str = "USD"
    type: str  # debit, credit
    frequency: str  # weekly, monthly, quarterly, yearly, custom
    interval_count: Optional[int] = None
    interval_unit: Optional[str] = None  # days, weeks, months, years; for custom only
    weekend_adjustment: WeekendAdjustment = "none"
    day_of_month: Optional[int] = None
    start_date: _Date
    end_date: Optional[_Date] = None
    account_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    skip_first: bool = False  # Set true when first occurrence already created as a transaction
    auto_generate: bool = True  # Materialize occurrences; when false, wait for the real charge
    notification_offsets: list[int] = []
    notify_overdue_daily: bool = False


class RecurringTransactionUpdate(BaseModel):
    description: Optional[str] = None
    notes: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    frequency: Optional[str] = None  # weekly, monthly, quarterly, yearly, custom
    interval_count: Optional[int] = None
    interval_unit: Optional[str] = None
    weekend_adjustment: Optional[WeekendAdjustment] = None
    day_of_month: Optional[int] = None
    start_date: Optional[_Date] = None
    end_date: Optional[_Date] = None
    account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    auto_generate: Optional[bool] = None
    notification_offsets: Optional[list[int]] = None
    notify_overdue_daily: Optional[bool] = None


class RecurringTransactionRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    description: str
    notes: Optional[str] = None
    amount: Decimal
    currency: str
    type: str
    frequency: str
    interval_count: Optional[int] = None
    interval_unit: Optional[str] = None
    weekend_adjustment: WeekendAdjustment = "none"
    day_of_month: Optional[int] = None
    start_date: _Date
    end_date: Optional[_Date] = None
    is_active: bool
    auto_generate: bool = True
    notification_offsets: list[int] = []
    notify_overdue_daily: bool = False
    next_occurrence: _Date
    amount_primary: Optional[float] = None
    fx_rate_used: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
