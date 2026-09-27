# CS 499 Enhancement:
# Separates injection API endpoints from the original monolithic application
# and delegates injection processing and inventory-related business logic
# to a dedicated service layer.

from fastapi import APIRouter

from models.injection import InjectionRecord
from services.injection_service import (
create_injection,
update_injection_by_id,
delete_injection_by_id,
get_all_injection_history,
get_injection_schedule_data,
)

router = APIRouter()

@router.post("/add_injection")
def add_injection(record: InjectionRecord):
        return create_injection(record)
   

@router.put("/update_injection/{injection_id}")
def update_injection(injection_id: str, record: InjectionRecord):
        return update_injection_by_id(injection_id, record)
   

@router.delete("/delete_injection/{injection_id}")
def delete_injection(injection_id: str):
        return delete_injection_by_id(injection_id)
   

@router.get("/injection_history")
def get_injection_history():
    return get_all_injection_history()

@router.get("/injection_schedule")
def get_injection_schedule():
    return get_injection_schedule_data()