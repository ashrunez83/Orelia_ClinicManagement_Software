# CS 499 Enhancement:
# Separates lab-related API endpoints from the original monolithic
# application structure and uses centralized handling for unexpected errors.


import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from database import execute_query
from models.lab import LabRecord


router = APIRouter()

@router.post("/add_lab")
def add_lab(record: LabRecord):
    patient_rows = execute_query("""
        SELECT patient_id
        FROM patients
        WHERE patient_uuid = %s
    """, (str(record.patient_uuid),))

    if not patient_rows:
        return JSONResponse(
            status_code=404,
            content={"error": "Patient not found."}
        )

    patient_id = patient_rows[0][0]

    execute_query("""
        INSERT INTO labs (
            lab_id,
            patient_id,
            patient_uuid,
            lab_type,
            ordered_date,
            completed_date,
            results_status,
            next_due_date,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        str(uuid.uuid4()),
        patient_id,
        str(record.patient_uuid),
        record.lab_type,
        record.ordered_date,
        record.completed_date,
        record.results_status,
        record.next_due_date,
        record.notes
    ), fetch=False)

    return {"message": "Lab record added successfully"}


@router.put("/update_lab/{lab_id}")
def update_lab(lab_id: str, record: LabRecord):
    execute_query("""
        UPDATE labs
        SET
            lab_type=%s,
            ordered_date=%s,
            completed_date=%s,
            results_status=%s,
            next_due_date=%s,
            notes=%s
        WHERE lab_id=%s
    """, (
        record.lab_type,
        record.ordered_date,
        record.completed_date,
        record.results_status,
        record.next_due_date,
        record.notes,
        lab_id
    ), fetch=False)

    return {"message": "Lab updated"}


@router.get("/labs")
def get_labs():
    rows = execute_query("""
        SELECT lab_id, patient_id, lab_type, ordered_date, completed_date,
               results_status, next_due_date, notes, patient_uuid
        FROM labs
        ORDER BY ordered_date DESC NULLS LAST;
    """)

    return [
        {
            "lab_id": str(r[0]),
            "patient_id": r[1],
            "lab_type": r[2],
            "ordered_date": str(r[3]) if r[3] else None,
            "completed_date": str(r[4]) if r[4] else None,
            "results_status": r[5],
            "next_due_date": str(r[6]) if r[6] else None,
            "notes": r[7],
            "patient_uuid": str(r[8]) if r[8] else None,
        }
        for r in rows
    ]


@router.get("/lab_reminders")
def get_lab_reminders():
    rows = execute_query("""
        SELECT *
        FROM lab_reminders
    """)

    if not rows:
        return []

    results = []

    for row in rows:
        row_dict = {}

        for i, value in enumerate(row):
            row_dict[f"col_{i}"] = (
                str(value) if value is not None else None
            )

        results.append(row_dict)

    return results