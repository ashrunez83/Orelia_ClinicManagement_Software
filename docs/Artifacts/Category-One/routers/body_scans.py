# CS 499 Enhancement:
# Separates body scan API endpoints from the original monolithic application
# structure and uses centralized handling for unexpected errors while
# preserving intentional client-facing responses.

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from database import execute_query
from models.body_scan import BodyScanRecord


router = APIRouter()


@router.post("/add_body_scan")
def add_body_scan(record: BodyScanRecord):
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
        INSERT INTO body_scans (
            patient_id,
            patient_uuid,
            scan_completed,
            scan_date,
            notes
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        patient_id,
        str(record.patient_uuid),
        record.scan_completed,
        record.scan_date,
        record.notes
    ), fetch=False)

    return {"message": "Body scan added"}


@router.get("/body_scans")
def get_body_scans():
    rows = execute_query("""
        SELECT patient_uuid, scan_date, notes
        FROM body_scans
        ORDER BY scan_date DESC;
    """)

    return [
        {
            "patient_uuid": str(r[0]),
            "scan_date": str(r[1]) if r[1] else None,
            "notes": r[2]
        }
        for r in rows
    ]