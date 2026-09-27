# CS 499 Enhancement:
# Separates treatment-related API endpoints from the original monolithic
# application structure and uses centralized handling for unexpected errors.

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from database import execute_query
from models.treatment import TreatmentRecord

router = APIRouter()


@router.get("/treatments")
def get_treatments():
    rows = execute_query("""
        SELECT treatment_id, patient_id, treatment_name, dosage, unit, frequency,
               start_date, end_date, status, notes, patient_uuid
        FROM treatments
        ORDER BY start_date DESC NULLS LAST;
    """)

    return [
        {
            "treatment_id": str(r[0]),
            "patient_id": r[1],
            "treatment_name": r[2],
            "dosage": float(r[3]) if r[3] is not None else None,
            "unit": r[4],
            "frequency": r[5],
            "start_date": str(r[6]) if r[6] else None,
            "end_date": str(r[7]) if r[7] else None,
            "status": r[8],
            "notes": r[9],
            "patient_uuid": str(r[10]) if r[10] else None,
        }
        for r in rows
    ]


@router.post("/add_treatment")
def add_treatment(record: TreatmentRecord):
    patient_rows = execute_query("""
        SELECT patient_id
        FROM patients
        WHERE patient_uuid = %s
    """, (record.patient_uuid,))

    if not patient_rows:
        return JSONResponse(
            status_code=404,
            content={"error": "Patient not found."}
        )

    patient_id = patient_rows[0][0]

    execute_query("""
        INSERT INTO treatments (
            patient_id,
            patient_uuid,
            treatment_name,
            dosage,
            unit,
            frequency,
            start_date,
            end_date,
            status,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        patient_id,
        record.patient_uuid,
        record.treatment_name,
        record.dosage,
        record.unit,
        record.frequency,
        record.start_date,
        record.end_date,
        record.status,
        record.notes
    ), fetch=False)

    return {"message": "Treatment added successfully"}