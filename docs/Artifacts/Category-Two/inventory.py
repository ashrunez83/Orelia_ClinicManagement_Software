# CS 499 Category Two Enhancement:
# Adds expiration-date information required by the FEFO inventory
# allocation algorithm while preserving compatibility with existing
# inventory records that do not yet contain an expiration date.

from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class InventoryItem(BaseModel):
    item_name: str
    lot_number: str
    quantity: float = Field(ge=0)
    unit: str
    reorder_level: float = Field(ge=0)
    ml_per_vial: Optional[float] = Field(default=None, gt=0)
    mg_per_ml: Optional[float] = Field(default=None, gt=0)
    expiration_date: Optional[date] = None
