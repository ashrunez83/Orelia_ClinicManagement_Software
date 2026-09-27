# CS 499 Enhancement:
# Separates injection business logic from API routing, including
# inventory deductions, transaction management, and error handling.

from fastapi import HTTPException
from database import get_db_connection, execute_query
from models.injection import InjectionRecord

import json

def create_injection(record: InjectionRecord):
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT quantity, reorder_level, ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (record.drug_name, record.lot_number))

        inventory_row = cur.fetchone()

        if not inventory_row:
            raise HTTPException(
                status_code=404,
                detail="Inventory Item not found"
            )
    
        current_quantity = float(inventory_row[0])
        reorder_level = float(inventory_row[1])
        ml_per_vial = inventory_row[2] or inventory_row[3]

        if not ml_per_vial:
            raise HTTPException(
                status_code=400,
                detail="Missing mL per vial for this inventory item."
            )
        
# Convert doses recorded in units to mL before calculating
# the corresponding inventory deduction.
        dose_ml = (
            float(record.dose) / 100
            if record.unit == "units"
            else float(record.dose)
        )

        actual_deduction = dose_ml / float(ml_per_vial)

        if current_quantity < actual_deduction:
            raise HTTPException(
                status_code=409,
                detail="Insufficient inventory."
            )

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

    except Exception:
        if conn:
            conn.rollback()
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def update_injection_by_id(injection_id: str, record: InjectionRecord):
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get original injection
        cur.execute("""
            SELECT drug_name, lot_number, dose, unit
            FROM injection_history
            WHERE injection_id = %s
        """, (injection_id,))

        original = cur.fetchone()

        if not original:
            raise HTTPException(
                status_code=404,
                detail="Injection not found"
            )

        old_drug, old_lot, old_dose, old_unit = original

        # Restore inventory used by original injection
        cur.execute("""
            SELECT ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (old_drug, old_lot))

        old_inventory = cur.fetchone()

        if not old_inventory:
            conn.rollback()
            raise HTTPException(
                status_code=404,
                detail="Original inventory item not found"
            )

        old_ml_per_vial = old_inventory[0] or old_inventory[1]
        old_dose_ml = (
            float(old_dose) / 100
            if old_unit == "units"
            else float(old_dose)
        )
        old_restore = old_dose_ml / float(old_ml_per_vial)

        cur.execute("""
            UPDATE inventory
            SET quantity = quantity + %s
            WHERE item_name = %s AND lot_number = %s
        """, (old_restore, old_drug, old_lot))

        # Get inventory for updated injection
        cur.execute("""
            SELECT quantity, ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (record.drug_name, record.lot_number))

        new_inventory = cur.fetchone()

        if not new_inventory:
            conn.rollback()
            raise HTTPException(
                status_code=404,
                detail="New inventory item not found"
            )

        current_qty = float(new_inventory[0])
        new_ml_per_vial = new_inventory[1] or new_inventory[2]

        if not new_ml_per_vial:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail="Missing mL per vial for updated medication"
            )

        new_dose_ml = (
            float(record.dose) / 100
            if record.unit == "units"
            else float(record.dose)
        )
        new_deduction = new_dose_ml / float(new_ml_per_vial)

        if current_qty < new_deduction:
            conn.rollback()
            raise HTTPException(
                status_code=409,
                detail="Insufficient inventory for update"
            )

        # Apply updated inventory deduction
        cur.execute("""
            UPDATE inventory
            SET quantity = quantity - %s
            WHERE item_name = %s AND lot_number = %s
        """, (
            new_deduction,
            record.drug_name,
            record.lot_number
        ))

        # Update injection record
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

    except Exception:
        if conn:
            conn.rollback()
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def delete_injection_by_id(injection_id: str):
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get injection before deleting it
        cur.execute("""
            SELECT drug_name, lot_number, dose, unit
            FROM injection_history
            WHERE injection_id = %s
        """, (injection_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Injection not found"
            )

        drug_name, lot_number, dose, unit = row
        dose = float(dose)

        # Get inventory information
        cur.execute("""
            SELECT ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s AND lot_number = %s
        """, (drug_name, lot_number))

        inventory_row = cur.fetchone()

        if not inventory_row:
            conn.rollback()
            raise HTTPException(
                status_code=404,
                detail="Inventory item not found"
            )

        ml_per_vial = inventory_row[0] or inventory_row[1]

        if not ml_per_vial:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail="Missing mL per vial for inventory item"
            )

        # Calculate amount to restore
        dose_ml = dose / 100 if unit == "units" else dose
        restore_amount = dose_ml / float(ml_per_vial)

        # Restore inventory
        cur.execute("""
            UPDATE inventory
            SET quantity = quantity + %s
            WHERE item_name = %s AND lot_number = %s
        """, (
            restore_amount,
            drug_name,
            lot_number
        ))

        # Delete injection
        cur.execute("""
            DELETE FROM injection_history
            WHERE injection_id = %s
        """, (injection_id,))

        # Record deletion in audit log
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

    except Exception:
        if conn:
            conn.rollback()
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_all_injection_history():
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


def get_injection_schedule_data():
    rows = execute_query("""
        SELECT *
        FROM injection_schedule
    """)

    if not rows:
        return []

    column_names = [
        "patient_uuid",
        "drug_name",
        "dose",
        "unit",
        "frequency_days",
        "next_due_date"
    ]

    results = []

    for row in rows:
        row_dict = {}

        for i, value in enumerate(row):
            if i < len(column_names):
                row_dict[column_names[i]] = (
                    str(value) if value is not None else None
                )

        results.append(row_dict)

    return results