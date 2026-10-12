from fastapi import FastAPI
from fastapi.responses import JSONResponse
import psycopg2
from pydantic import BaseModel
from typing import Optional, List
import datetime
from datetime import date, timedelta
import json
import uuid
import os
from pydantic import Field

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.head("/")
def root_head():
    return {"status": "ok"}

# -------------------------------
# CONFIG
# ------------------------------
def get_env(name):
    value = os.getenv(name)
    return value.strip() if value else None


DB_HOST = get_env("DB_HOST")
DB_PORT = get_env("DB_PORT") or "5432"
DB_NAME = get_env("DB_NAME")
DB_USER = get_env("DB_USER")
DB_PASSWORD = get_env("DB_PASSWORD")


# -------------------------------
# DB HELPER
# -------------------------------
def get_db_connection():
    missing = [
        name for name, value in {
            "DB_HOST": DB_HOST,
            "DB_PORT": DB_PORT,
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            f"Missing database environment variables: {', '.join(missing)}"
        )

    return psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def execute_query(query, params=None, fetch=True):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(query, params or ())
        if fetch:
            result = cur.fetchall()
        else:
            result = None
        conn.commit()
        return result
    finally:
        cur.close()
        conn.close()


def database_config_summary():
    missing = [
        name for name, value in {
            "DB_HOST": DB_HOST,
            "DB_PORT": DB_PORT,
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
        }.items()
        if not value
    ]

    return {
        "configured": not missing,
        "source": "DB_* env vars",
        "scheme": "postgresql",
        "username": DB_USER,
        "hostname": DB_HOST,
        "port": int(DB_PORT) if DB_PORT else None,
        "database": DB_NAME,
        "missing": missing,
    }
@app.get("/debug/db")
def debug_db():
    summary = database_config_summary()

    try:
        rows = execute_query("SELECT 1;")
        return {
            **summary,
            "connection_ok": True,
            "test_result": rows[0][0] if rows else None,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                **summary,
                "connection_ok": False,
                "error": str(e),
            },
        )


# -------------------------------
# MODELS
# -------------------------------
class InjectionRecord(BaseModel):
    patient_uuid: str
    drug_name: str
    lot_number: Optional[str] = None
    dose: float
    unit: str = "mL"
    injection_date: datetime.datetime = Field(default_factory=datetime.datetime.now)
    frequency_days: Optional[int] = None
    date_paid: Optional[datetime.datetime] = None
    labs_done: bool = False
    lab_date: Optional[datetime.datetime] = None
    weight: Optional[float] = None
    notes: Optional[str] = None
    anastrozole_mg: Optional[float] = None


class InventoryItem(BaseModel):
    item_name: str
    lot_number: str
    quantity: float
    unit: str
    reorder_level: float
    ml_per_vial: Optional[float] = None
    mg_per_ml: Optional[float] = None

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    phone: str
    email: str
    pre_lab_date: Optional[str] = None
    testosterone_level: Optional[float] = None

class LabRecord(BaseModel):
    patient_uuid: str
    lab_type: str
    ordered_date: Optional[str] = None
    completed_date: Optional[str] = None
    results_status: Optional[str] = None
    next_due_date: Optional[str] = None
    notes: Optional[str] = None

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

class BodyScanRecord(BaseModel):
    patient_uuid: str
    scan_completed: Optional[bool] = False
    scan_date: Optional[str] = None
    notes: Optional[str] = None

class PatientUpdate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    phone: str
    email: str
    pre_lab_date: Optional[str] = None
    testosterone_level: Optional[float] = None

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




# -------------------------------
# ROOT
# -------------------------------
@app.get("/")
def home():
    return {"message": "API running"}


# -------------------------------
# PATIENTS
# -------------------------------

@app.get("/patients")
def get_patients():
    try:
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
    except Exception as e:
        print("GET PATIENTS ERROR:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/add_patient")
def add_patient(data: PatientCreate):
    try:
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
    except Exception as e:
        print("ADD PATIENT ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/search_patients")
def search_patients(first_name: str = "", last_name: str = ""):
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

@app.get("/patient_detail/{patient_uuid}")
def get_patient_detail(patient_uuid: str):
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

@app.post("/add_body_scan")
def add_body_scan(record: BodyScanRecord):
    try:
        patient_rows = execute_query("""
            SELECT patient_id
            FROM patients
            WHERE patient_uuid = %s
        """, (record.patient_uuid,))

        if not patient_rows:
            return JSONResponse(status_code=404, content={"error": "Patient not found."})
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
    
    except Exception as e:
        print("ADD BODY SCAN ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})
    
@app.get("/body_scans")
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
                                            
# -------------------------------
# INJECTIONS
# -------------------------------
@app.post("/add_injection")
def add_injection(record: InjectionRecord):

    conn = None
    cur = None
    try:
        print("INJECTION PAYLOAD:", record.dict())  # 
        conn = get_db_connection()
        cur = conn.cursor()


        cur.execute("""
            SELECT quantity, reorder_level, ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (record.drug_name, record.lot_number))

        inventory_row = cur.fetchone()

        if not inventory_row:
            return {"error": "Inventory item not found"}

        current_quantity = float(inventory_row[0])
        reorder_level = float(inventory_row[1])
        ml_per_vial = inventory_row[2] or inventory_row[3]

        if not ml_per_vial:
            return {"error": "Missing mL per vial for this inventory item."}

        dose_ml = float(record.dose) / 100 if record.unit == "units" else float(record.dose)
        actual_deduction = dose_ml / float(ml_per_vial)

        print(f"💉 Deducting {actual_deduction:.4f} vial(s) from {record.drug_name} (Lot: {record.lot_number})")

        if current_quantity < actual_deduction:
            return {"error": "Insufficient inventory."}

        cur.execute("""
            UPDATE inventory
            SET quantity = quantity - %s
            WHERE item_name = %s 
              AND lot_number = %s
            RETURNING quantity, reorder_level
        """, (
            actual_deduction,
            record.drug_name,
            record.lot_number
        ))

        updated_row = cur.fetchone()
        new_quantity = float(updated_row[0])
        reorder_level = float(updated_row[1])

        cur.execute("""
            INSERT INTO injection_history (
                patient_uuid,
                drug_name,
                lot_number,
                dose,
                unit,
                injection_date,
                frequency_days,
                date_paid,
                labs_done,
                lab_date,
                weight,
                notes,
                anastrozole_mg
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            record.patient_uuid,
            record.drug_name,
            record.lot_number,
            record.dose,
            record.unit,
            record.injection_date,
            record.frequency_days,
            record.date_paid,
            record.labs_done,
            record.lab_date,
            record.weight,
            record.notes,
            record.anastrozole_mg
        ))

        conn.commit()

        return {
            "message": "Injection added",
            "remaining_quantity": new_quantity,
            "low_stock": new_quantity <= reorder_level
        }

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR:", e)
        print("❌ INJECTION ERROR:", e)   # ✅ ADD THIS
        return JSONResponse(status_code=400, content={"error": str(e)})

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.put("/update_injection/{injection_id}")
def update_injection(injection_id: str, record: InjectionRecord):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # -------------------------------
        # 1. GET ORIGINAL INJECTION
        # -------------------------------
        cur.execute("""
            SELECT drug_name, lot_number, dose, unit
            FROM injection_history
            WHERE injection_id = %s
        """, (injection_id,))

        original = cur.fetchone()

        if not original:
            return {"error": "Injection not found"}

        old_drug, old_lot, old_dose, old_unit = original

        # -------------------------------
        # 2. RESTORE OLD INVENTORY (FIXED)
        # -------------------------------
        cur.execute("""
            SELECT ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (old_drug, old_lot))

        old_inventory = cur.fetchone()

        if not old_inventory:
            conn.rollback()
            return {"error": "Original inventory item not found"}

        old_ml_per_vial = old_inventory[0] or old_inventory[1]
        old_dose_ml = float(old_dose) / 100 if old_unit == "units" else float(old_dose)
        old_restore = old_dose_ml / float(old_ml_per_vial)

        print(f"🔁 Restoring {old_restore:.4f} vial(s) back to {old_drug} (Lot: {old_lot})")


        cur.execute("""
            UPDATE inventory
            SET quantity = quantity + %s
            WHERE item_name = %s AND lot_number = %s
        """, (old_restore, old_drug, old_lot))

        # -------------------------------
        # 3. GET NEW INVENTORY + CALC DEDUCTION (FIXED)
        # -------------------------------
        cur.execute("""
            SELECT quantity, ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (record.drug_name, record.lot_number))

        new_inventory = cur.fetchone()

        if not new_inventory:
            conn.rollback()
            return {"error": "New inventory item not found"}

        current_qty = float(new_inventory[0])
        new_ml_per_vial = new_inventory[1] or new_inventory[2]

        if not new_ml_per_vial:
            conn.rollback()
            return {"error": "Missing mL per vial for updated medication"}

        new_dose_ml = float(record.dose) / 100 if record.unit == "units" else float(record.dose)
        new_deduction = new_dose_ml / float(new_ml_per_vial)

        print(f"💉 Deducting {new_deduction:.4f} vial(s) from {record.drug_name} (Lot: {record.lot_number})")

        if current_qty < new_deduction:
            conn.rollback()
            return {"error": "Insufficient inventory for update"}

        # -------------------------------
        # 4. APPLY NEW DEDUCTION (FIXED)
        # -------------------------------
        cur.execute("""
            UPDATE inventory
            SET quantity = quantity - %s
            WHERE item_name = %s AND lot_number = %s
        """, (new_deduction, record.drug_name, record.lot_number))

        # -------------------------------
        # 5. UPDATE INJECTION RECORD
        # -------------------------------
        cur.execute("""
            UPDATE injection_history
            SET
                drug_name = %s,
                lot_number = %s,
                dose = %s,
                unit = %s,
                injection_date = %s,
                frequency_days = %s,
                date_paid = %s,
                labs_done = %s,
                lab_date = %s,
                weight = %s,
                notes = %s,
                anastrozole_mg = %s
            WHERE injection_id = %s
        """, (
            record.drug_name,
            record.lot_number,
            record.dose,
            record.unit,
            record.injection_date,
            record.frequency_days,
            record.date_paid,
            record.labs_done,
            record.lab_date,
            record.weight,
            record.notes,
            record.anastrozole_mg,
            injection_id
        ))

        conn.commit()
        return {"message": "Injection updated successfully"}

    except Exception as e:
        if conn:
            conn.rollback()
        return JSONResponse(status_code=400, content={"error": str(e)})

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.delete("/delete_injection/{injection_id}")
def delete_injection(injection_id: str):

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # -------------------------------
        # 1. GET INJECTION
        # -------------------------------
        cur.execute("""
            SELECT drug_name, lot_number, dose, unit
            FROM injection_history
            WHERE injection_id = %s
        """, (injection_id,))

        row = cur.fetchone()

        if not row:
            return {"error": "Injection not found"}

        drug_name, lot_number, dose, unit = row
        dose = float(dose)

        # -------------------------------
        # 2. RESTORE INVENTORY
        # -------------------------------
        cur.execute("""
            SELECT ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (drug_name, lot_number))
        inventory_row = cur.fetchone()

        if not inventory_row:
            conn.rollback()
            return {"error": "Inventory item not found"}

        ml_per_vial = inventory_row[0] or inventory_row[1]

        if not ml_per_vial:
            conn.rollback()
            return {"error": "Missing mL per vial for inventory item"}

        dose_ml = dose / 100 if unit == "units" else dose
        restore_amount = dose_ml / float(ml_per_vial)

        print(f"🗑️ Restoring {restore_amount:.4f} vial(s) to {drug_name} (Lot: {lot_number}) from deleted injection")
        cur.execute("""
            UPDATE inventory
            SET quantity = quantity + %s
            WHERE item_name = %s AND lot_number = %s
        """, (restore_amount, drug_name, lot_number))
        # -------------------------------
        # 3. DELETE INJECTION
        # -------------------------------
        cur.execute("""
            DELETE FROM injection_history
            WHERE injection_id = %s
        """, (injection_id,))

        # -------------------------------
        # 4. AUDIT LOG
        # -------------------------------
        cur.execute("""
            INSERT INTO audit_log (
                action_type,
                entity_type,
                entity_id,
                user_name,
                details
            )
            VALUES (%s,%s,%s,%s,%s)
        """, (
            "DELETE",
            "injection",
            injection_id,
            "admin",
            json.dumps({
                "dose": dose,
                "inventory_restored": restore_amount
            })
        ))

        conn.commit()

        return {"message": "Injection deleted successfully"}

    except Exception as e:
        if conn:
            conn.rollback()
        return JSONResponse(status_code=400, content={"error": str(e)})

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.post("/add_lab")
def add_lab(record: LabRecord):
    try:
        print("LAB PAYLOAD:", record.dict())

        # ✅ FIXED HERE
        patient_rows = execute_query("""
            SELECT patient_id
            FROM patients
            WHERE patient_uuid = %s
        """, (str(record.patient_uuid),))

        if not patient_rows:
            return JSONResponse(status_code=404, content={"error": "Patient not found."})

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
            str(uuid.uuid4()),  # ✅ also safer as string
            patient_id,
            str(record.patient_uuid),  # ✅ you already fixed this
            record.lab_type,
            record.ordered_date,
            record.completed_date,
            record.results_status,
            record.next_due_date,
            record.notes
        ), fetch=False)

        return {"message": "Lab record added successfully"}

    except Exception as e:
        print("❌ LAB ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})




@app.put("/update_lab/{lab_id}")
def update_lab(lab_id: str, record: LabRecord):
    try:
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
    except Exception as e:
        print("UPDATE LAB ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})

# -------------------------------
# PATIENTS
# -------------------------------
@app.put("/update_patient/{patient_uuid}")
def update_patient(patient_uuid: str, data: PatientUpdate):
    try:
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
    except Exception as e:
        print("UPDATE PATIENT ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})

# -------------------------------
# PAYMENTS (UPDATED)
# -------------------------------
@app.post("/add_payment")
def add_payment(data: PaymentModel):

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # -------------------------------
        # AUTO TESTOSTERONE PRICING
        # -------------------------------
        if data.payment_type == "Testosterone Plan":
            if data.lab_package == "No Labs ($165)":
                data.amount = 165
            elif data.lab_package == "Labs $110":
                data.amount = 110
            elif data.lab_package == "Labs $190":
                data.amount = 190

        cur.execute("""
            INSERT INTO payments(
                payment_id,
                patient_uuid,
                payment_date,
                amount,
                payment_method,
                notes,
                autopay,
                payment_type,
                lab_package,
                payment_frequency_days,
                next_payment_due
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(uuid.uuid4()),
            data.patient_uuid,
            data.payment_date,
            data.amount,
            data.payment_method,
            data.notes,
            data.autopay,
            data.payment_type,
            data.lab_package,
            data.payment_frequency_days,
            data.next_payment_due
        ))

        conn.commit()
        return {"message": "Payment added"}

    except Exception as e:
        if conn:
            conn.rollback()
        return JSONResponse(status_code=400, content={"error": str(e)})

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.get("/payments")
def get_payments():
    rows = execute_query("""
        SELECT 
            payment_id,
            patient_uuid,
            payment_date,
            amount,
            payment_method,
            notes,
            autopay,
            payment_type,
            lab_package,
            payment_frequency_days,
            next_payment_due
        FROM payments
        ORDER BY payment_date DESC
    """)

    return [{
        "payment_id": str(r[0]),
        "patient_uuid": str(r[1]),
        "payment_date": str(r[2]),
        "amount": float(r[3]),
        "payment_method": r[4],
        "notes": r[5],
        "autopay": r[6],
        "payment_type": r[7],
        "lab_package": r[8],
        "payment_frequency_days": r[9],
        "next_payment_due": str(r[10]) if r[10] else None
    } for r in rows]

@app.put("/update_payment/{payment_id}")
def update_payment(payment_id: str, data: PaymentModel):

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE payments
            SET
                amount = %s,
                payment_date = %s,
                payment_method = %s,
                notes = %s,
                autopay = %s,
                payment_type = %s,
                lab_package = %s,
                payment_frequency_days = %s,
                next_payment_due = %s
            WHERE payment_id = %s
        """, (
            data.amount,
            data.payment_date,
            data.payment_method,
            data.notes,
            data.autopay,
            data.payment_type,
            data.lab_package,
            data.payment_frequency_days,
            data.next_payment_due,
            payment_id
        ))

        conn.commit()
        return {"message": "Payment updated"}

    except Exception as e:
        if conn:
            conn.rollback()
        return JSONResponse(status_code=400, content={"error": str(e)})

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.delete("/delete_payment/{payment_id}")
def delete_payment(payment_id: str):
    try:
        execute_query("""
            DELETE FROM payments
            WHERE payment_id = %s
        """, (payment_id,), fetch=False)

        return {"message": "Payment deleted"}
    except Exception as e:
        print("DELETE PAYMENT ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})

# -------------------------------
# INVENTORY FIX (REMOVED DUPLICATE ENDPOINT)
# -------------------------------
@app.put("/update_inventory/{inventory_id}")
def update_inventory(inventory_id: str, item: dict):
    try:
        execute_query("""
            UPDATE inventory
            SET item_name=%s,
                lot_number=%s,
                quantity=%s,
                unit=%s,
                reorder_level=%s,
                ml_per_vial=%s,
                mg_per_ml=%s
            WHERE inventory_id=%s
        """, (
            item["item_name"],
            item["lot_number"],
            item["quantity"],
            item["unit"],
            item["reorder_level"],
            item.get("ml_per_vial"),
            item.get("mg_per_ml"),
            inventory_id
        ), fetch=False)

        return {"message": "Inventory updated"}
    except Exception as e:
        print("UPDATE INVENTORY ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/injection_history")
def get_injection_history():
    rows = execute_query("""
        SELECT
            injection_id,
            patient_uuid,
            drug_name,
            dose,
            unit,
            injection_date,
            frequency_days,
            date_paid,
            labs_done,
            lab_date,
            weight,
            notes,
            anastrozole_mg
        FROM injection_history
        ORDER BY injection_date DESC;
    """)

    return [
        {
            "injection_id": str(r[0]),
            "patient_uuid": str(r[1]),
            "drug_name": r[2],
            "dose": r[3],
            "unit": r[4],
            "injection_date": str(r[5]) if r[5] else None,
            "frequency_days": r[6],
            "date_paid": str(r[7]) if r[7] else None,
            "labs_done": r[8],
            "lab_date": str(r[9]) if r[9] else None,
            "weight": float(r[10]) if r[10] else None,
            "notes": r[11],
            "anastrozole_mg": float(r[12]) if r[12] is not None else None
        }
        for r in rows
    ]

@app.get("/injection_schedule")
def get_injection_schedule():
    rows = execute_query("""
        SELECT*                   
        FROM injection_schedule
    """)

    if not rows:
        return []

    column_names = [
        "patient_uuid", "drug_name", "dose", "unit", "frequency_days", "next_due_date"
    ]

    results = []
    for row in rows:
        row_dict = {}
        for i, value in enumerate(row):
            if i < len(column_names):
                row_dict[column_names[i]] = str(value) if value is not None else None
        results.append(row_dict)

    return results

@app.get("/labs")
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

@app.get("/lab_reminders")
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
            row_dict[f"col_{i}"] = str(value) if value is not None else None
        results.append(row_dict)

    return results

@app.get("/treatments")
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
@app.post("/add_treatment")
def add_treatment(record: TreatmentRecord):
    try:
        patient_rows = execute_query("""
            SELECT patient_id
            FROM patients
            WHERE patient_uuid = %s
        """, (record.patient_uuid,))

        if not patient_rows:
            return JSONResponse(status_code=404, content={"error": "Patient not found."})

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
    except Exception as e:
        print("ADD TREATMENT ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})

# -------------------------------
# INVENTORY
# -------------------------------
@app.get("/inventory")
def get_inventory():
    rows = execute_query("""
        SELECT 
            inventory_id,
            inventory_uuid,
            item_name,
            lot_number,
            quantity,
            unit,
            reorder_level,
            concentration_ml_per_vial,
            ml_per_vial,
            mg_per_ml
        FROM inventory
        ORDER BY item_name
    """)

    return [
        {
            "inventory_id": str(r[0]),
            "inventory_uuid": str(r[1]) if r[1] else None,
            "item_name": r[2],
            "lot_number": r[3],
            "quantity": float(r[4]) if r[4] is not None else 0,
            "unit": r[5],
            "reorder_level": float(r[6]) if r[6] is not None else 0,
            "concentration_ml_per_vial": float(r[7]) if r[7] is not None else None,
            "ml_per_vial": float(r[8]) if r[8] is not None else None,
            "mg_per_ml": float(r[9]) if r[9] is not None else None,
        }
        for r in rows
    ]


@app.post("/add_inventory")
def add_inventory(item: InventoryItem):
    try:
        execute_query("""
            INSERT INTO inventory (
                item_name,
                lot_number,
                quantity,
                unit,
                reorder_level,
                concentration_ml_per_vial,
                ml_per_vial,
                mg_per_ml
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            item.item_name,
            item.lot_number,
            item.quantity,
            item.unit,
            item.reorder_level,
            item.ml_per_vial,
            item.ml_per_vial,
            item.mg_per_ml
        ), fetch=False)

        return {"message": "Inventory added"}
    except Exception as e:
        print("ADD INVENTORY ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.delete("/delete_inventory/{inventory_id}")
def delete_inventory(inventory_id: str):
    try:
        execute_query("""
            DELETE FROM inventory WHERE inventory_id=%s
        """, (inventory_id,), fetch=False)

        return {"message": "Deleted"}
    except Exception as e:
        print("DELETE INVENTORY ERROR:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})

