from pydantic import BaseModel
from typing import Optional

class TreatmentRecord(BaseModel):
    patient_uuid: str
    treatment_name: str
    dosage: Optional[float] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = "Active"
    notes: Optional[str] = None