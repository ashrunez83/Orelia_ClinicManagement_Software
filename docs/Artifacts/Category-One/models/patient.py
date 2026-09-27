from typing import Optional
from pydantic import BaseModel


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    phone: str
    email: str
    pre_lab_date: Optional[str] = None
    testosterone_level: Optional[float] = None

class PatientUpdate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    phone: str
    email: str
    pre_lab_date: Optional[str] = None
    testosterone_level: Optional[float] = None