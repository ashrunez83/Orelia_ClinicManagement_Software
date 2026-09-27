from pydantic import BaseModel
from typing import Optional



class PaymentModel(BaseModel):
    patient_uuid: str
    amount: float
    payment_date: str
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    autopay: Optional[str] = None
    payment_type: Optional[str] = None
    lab_package: Optional[str] = None
    payment_frequency_days: Optional[int] = None
    next_payment_due: Optional[str] = None
