# CS 499 Enhancement:
# Defines a dedicated Pydantic model for body scan data, separating
# request validation and data structure from API routing and supporting
# the application's modular architecture.

from pydantic import BaseModel
from typing import Optional

class BodyScanRecord(BaseModel):
    patient_uuid: str
    scan_completed: Optional[bool] = False
    scan_date: Optional[str] = None
    notes: Optional[str] = None