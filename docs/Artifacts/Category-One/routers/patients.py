# CS 499 Enhancement:
# Defines patient API routes while delegating database and business
# operations to the patient service layer.


from fastapi import APIRouter
from models.patient import PatientCreate, PatientUpdate

from models.patient import PatientCreate, PatientUpdate

from services.patient_service import (
get_all_patients, 
create_patient, 
search_patients_by_name,
get_patient_by_uuid,
update_patient_by_uuid
)

router = APIRouter()


@router.get("/patients")
def get_patients():
        return get_all_patients()

@router.post("/add_patient")
def add_patient(data: PatientCreate):
        return create_patient(data)
   
@router.get("/search_patients")
def search_patients(first_name: str = "", last_name: str = ""):
    return search_patients_by_name(first_name, last_name)

@router.get("/patient_detail/{patient_uuid}")
def get_patient_detail(patient_uuid: str):
    return get_patient_by_uuid(patient_uuid)

@router.put("/update_patient/{patient_uuid}")
def update_patient(patient_uuid: str, data: PatientUpdate):
        return update_patient_by_uuid(patient_uuid, data)
    