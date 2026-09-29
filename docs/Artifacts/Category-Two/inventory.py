# CS 499 Enhancement:
# Strengthens inventory validation by enforcing valid quantity,
# reorder, volume, and concentration values at the API boundary.

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
