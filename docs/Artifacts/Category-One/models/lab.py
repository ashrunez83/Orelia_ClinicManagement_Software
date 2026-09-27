from pydantic import BaseModel, Field
from typing import Optional



class LabRecord(BaseModel):
    patient_uuid: str
    lab_type: str
    ordered_date: Optional[str] = None
    completed_date: Optional[str] = None
    results_status: Optional[str] = None
    next_due_date: Optional[str] = None
    notes: Optional[str] = None

