# CS 499 Enhancement:
# Uses Pydantic validation to reject invalid injection data before
# the request reaches business logic or database operations.

import datetime

from pydantic import BaseModel, Field
from typing import Optional


class InjectionRecord(BaseModel):
    patient_uuid: str
    drug_name: str
    lot_number: Optional[str] = None
    dose: float = Field(gt=0) # Prevents zero or negative injection doses
    unit: str = "mL"
    injection_date: datetime.datetime = Field(default_factory=datetime.datetime.now)
    frequency_days: Optional[int] = None
    date_paid: Optional[datetime.datetime] = None
    labs_done: bool = False
    lab_date: Optional[datetime.datetime] = None
    weight: Optional[float] = None
    notes: Optional[str] = None
    anastrozole_mg: Optional[float] = None
