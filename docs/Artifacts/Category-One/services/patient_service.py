# CS 499 Enhancement:
# Encapsulates patient database operations in a service layer rather
# than coupling SQL operations directly to API routes.

from database import execute_query

def get_all_patients():
    rows = execute_query("""
        SELECT 
            patient_id,
            patient_uuid,
            first_name,
            last_name,
            date_of_birth,
            phone,
            email,
            pre_lab_date,
            testosterone_level
        FROM patients
        ORDER BY last_name, first_name;
    """)

    return [
        {
            "patient_id": r[0],
            "patient_uuid": str(r[1]),
            "first_name": r[2],
            "last_name": r[3],
            "date_of_birth": str(r[4]) if r[4] else None,
            "phone": r[5],
            "email": r[6],
            "pre_lab_date": str(r[7]) if r[7] else None,
            "testosterone_level": r[8]
        }
        for r in rows
    ]

def create_patient(data):
    execute_query("""
        INSERT INTO patients (
            first_name,
            last_name,
            date_of_birth,
            phone,
            email,
            pre_lab_date,
            testosterone_level
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        data.first_name,
        data.last_name,
        data.date_of_birth,
        data.phone,
        data.email,
        data.pre_lab_date,
        data.testosterone_level
    ), fetch=False)

    return {"message": "Patient added successfully"}

def search_patients_by_name(first_name: str = "", last_name: str = ""):
    first_name = first_name.strip()
    last_name = last_name.strip()

    rows = execute_query("""
        SELECT patient_id, patient_uuid, first_name, last_name, date_of_birth, phone, email
        FROM patients
        WHERE (%s = '' OR first_name ILIKE %s)
          AND (%s = '' OR last_name ILIKE %s)
        ORDER BY last_name, first_name;
    """, (
        first_name, f"%{first_name}%",
        last_name, f"%{last_name}%"
    ))

    return [
        {
            "patient_id": r[0],
            "patient_uuid": str(r[1]),
            "first_name": r[2],
            "last_name": r[3],
            "date_of_birth": str(r[4]),
            "phone": r[5],
            "email": r[6]
        }
        for r in rows
    ]

def get_patient_by_uuid(patient_uuid: str):
    rows = execute_query("""
        SELECT 
            patient_id,
            patient_uuid,
            first_name,
            last_name,
            date_of_birth,
            phone,
            email,
            pre_lab_date,
            testosterone_level
        FROM patients
        WHERE patient_uuid = %s
    """, (patient_uuid,))

    return [
        {
            "patient_id": r[0],
            "patient_uuid": str(r[1]),
            "first_name": r[2],
            "last_name": r[3],
            "date_of_birth": str(r[4]) if r[4] else None,
            "phone": r[5],
            "email": r[6],
            "pre_lab_date": str(r[7]) if r[7] else None,
            "testosterone_level": r[8] if len(r) > 8 else None
        }
        for r in rows
    ]

def update_patient_by_uuid(patient_uuid: str, data):
    execute_query("""
        UPDATE patients
        SET first_name=%s,
            last_name=%s,
            date_of_birth=%s,
            phone=%s,
            email=%s,
            pre_lab_date=%s,
            testosterone_level=%s
        WHERE patient_uuid=%s
    """, (
        data.first_name,
        data.last_name,
        data.date_of_birth,
        data.phone,
        data.email,
        data.pre_lab_date,
        data.testosterone_level,
        patient_uuid
    ), fetch=False)

    return {"message": "Patient updated"}