# CS 499 Enhancement:
# Separates injection business logic from API routing, including
# inventory deductions, transaction management, and error handling.

from fastapi import HTTPException
from database import get_db_connection, execute_query
from models.injection import InjectionRecord

import json

def apply_fefo_allocations(cur, allocations):
    """
    Apply previously calculated FEFO allocations to inventory
    Each inventory lot is updated individually so multi-lot allocations remain accurate
    and can be recorded for auditability.
    """

    for allocation in allocations:
        cur.execute("""
            UPDATE inventory
            SET quantity = quantity - %s
            WHERE inventory_id = %s
        """, (
            allocation["quantity_used"],
            allocation["inventory_id"]
        
        ))
def record_fefo_allocations(cur, injection_id: str, allocations):
    """
    Record the inventory lots used to fulfill an injection.
    """

    for allocation in allocations:
        cur.execute("""
            INSERT INTO injection_inventory_allocations (
                injection_id,
                inventory_id,
                lot_number,
                quantity_used,
                expiration_date
        )
        VALUES (%s, %s, %s, %s, %s)
        """, (
            injection_id,
            allocation["inventory_id"],
            allocation["lot_number"],
            allocation["quantity_used"],
            allocation["expiration_date"]
        ))

def restore_fefo_allocations(cur, injection_id: str):
    """
    Restore inventory quantities previously allocated to an injection.

    Each allocation is restored to its original inventory record so
    multi-lot FEFO deductions can be reversed accurately.
    """

    cur.execute("""
        SELECT
            inventory_id,
            quantity_used
        FROM injection_inventory_allocations
        WHERE injection_id = %s
    """, (injection_id,))

    allocations = cur.fetchall()

    for inventory_id, quantity_used in allocations:
        cur.execute("""
            UPDATE inventory
            SET quantity = quantity + %s
            WHERE inventory_id = %s
        """, (
            quantity_used,
            inventory_id
        ))

    return allocations       

def allocate_inventory_fefo(cur, drug_name: str, required_quantity: float):
    """
    Allocate inventory using First expired, First Out (FEFO).

    Eligible Inventory lots are ordered by expiration date so inventory
    expiring soonest is consumed first. The algorithm can allocate accross multiple lots
    when a single lot cannot satisfy the required quantiy.
    """

    cur.execute("""
        SELECT
            inventory_id,
            lot_number,
            quantity,
            expiration_date
        FROM inventory
        WHERE item_name = %s
          AND quantity > 0
          AND expiration_date IS NOT NULL
          AND expiration_date >= CURRENT_DATE
        ORDER BY expiration_date ASC
    """, (drug_name,))

    available_lots = cur.fetchall()

    if not available_lots:
        raise HTTPException(
            status_code=404,
            detail="No eligible inventory lots found."
        )
    total_available = sum(float(lot[2]) for lot in available_lots)
    if total_available < required_quantity:
        raise HTTPException(
            status_code=409,
            detail="Insufficient inventory across available lots."
        )
    remaining = required_quantity
    allocations = []

    #Traverse inventory in expiration date order and consume the earliest
    #expiring usable lot before moving to the next lot

    for inventory_id, lot_number, quantity, expiration_date in available_lots:
        if remaining <= 0:
            break

        available_quantity = float(quantity)
        deduction = min(available_quantity, remaining)

        allocations.append({
            "inventory_id": inventory_id,
            "lot_number": lot_number,
            "expiration_date": expiration_date,
            "quantity_used": deduction
        })

        remaining -= deduction
    return allocations


def create_injection(record: InjectionRecord):
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # CS 499 Category Two Enhancement:
        # Convert the requested dose into the inventory quantity required
        # before applying the FEFO allocation algorithm.

        dose_ml = (
            float(record.dose) / 100
            if record.unit == "units"
            else float(record.dose)
        )

        # Retrieve an eligible inventory lot to determine the medication's
        # mL-per-vial value used for inventory calculations.
        cur.execute("""
            SELECT ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s
              AND quantity > 0
              AND expiration_date IS NOT NULL
              AND expiration_date >= CURRENT_DATE
            ORDER BY expiration_date ASC
            LIMIT 1
        """, (record.drug_name,))

        inventory_row = cur.fetchone()

        if not inventory_row:
            raise HTTPException(
                status_code=404,
                detail="No eligible inventory lots found."
            )

        ml_per_vial = inventory_row[0] or inventory_row[1]

        if not ml_per_vial:
            raise HTTPException(
                status_code=400,
                detail="Missing mL per vial for this inventory item."
            )

        required_quantity = dose_ml / float(ml_per_vial)

        # Determine which inventory lots should satisfy the requested
        # quantity using First Expired, First Out (FEFO).
        allocations = allocate_inventory_fefo(
            cur,
            record.drug_name,
            required_quantity
        )

        # Apply all calculated inventory deductions inside the current
        # transaction. Nothing is committed until the entire operation succeeds.
        apply_fefo_allocations(cur, allocations)

        primary_lot = allocations[0]["lot_number"]

        # Create the injection record and retrieve its UUID so each FEFO
        # allocation can be associated with this injection.
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
            RETURNING injection_id
        """, (
            record.patient_uuid,
            record.drug_name,
            primary_lot,
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

        injection_id = cur.fetchone()[0]

        # Preserve the complete lot-by-lot allocation history.
        record_fefo_allocations(
            cur,
            injection_id,
            allocations
        )

        conn.commit()

        return {
            "message": "Injection added",
            "injection_id": str(injection_id),
            "inventory_allocation": [
                {
                    "lot_number": allocation["lot_number"],
                    "quantity_used": allocation["quantity_used"],
                    "expiration_date": str(allocation["expiration_date"])
                }
                for allocation in allocations
            ]
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

        # Retrieve the original injection for existence checking and
        # backward compatibility with pre-FEFO records.
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

        # CS 499 Category Two Enhancement:
        # Restore the exact FEFO allocations associated with the original
        # injection before calculating the updated allocation.
        old_allocations = restore_fefo_allocations(
            cur,
            injection_id
        )

        if not old_allocations:
            # Backward compatibility:
            # Pre-FEFO injections do not have allocation records, so restore
            # inventory using the original single-lot behavior.
            cur.execute("""
                SELECT ml_per_vial, concentration_ml_per_vial
                FROM inventory
                WHERE item_name = %s
                  AND lot_number = %s
            """, (
                old_drug,
                old_lot
            ))

            old_inventory = cur.fetchone()

            if not old_inventory:
                raise HTTPException(
                    status_code=404,
                    detail="Original inventory item not found"
                )

            old_ml_per_vial = old_inventory[0] or old_inventory[1]

            if not old_ml_per_vial:
                raise HTTPException(
                    status_code=400,
                    detail="Missing mL per vial for original inventory item"
                )

            old_dose_ml = (
                float(old_dose) / 100
                if old_unit == "units"
                else float(old_dose)
            )

            old_restore = old_dose_ml / float(old_ml_per_vial)

            cur.execute("""
                UPDATE inventory
                SET quantity = quantity + %s
                WHERE item_name = %s
                  AND lot_number = %s
            """, (
                old_restore,
                old_drug,
                old_lot
            ))

        # Remove the previous allocation records. They will be replaced
        # with the allocations calculated for the updated injection.
        cur.execute("""
            DELETE FROM injection_inventory_allocations
            WHERE injection_id = %s
        """, (injection_id,))

        # Determine the mL-per-vial value from the earliest eligible lot
        # for the updated medication.
        cur.execute("""
            SELECT ml_per_vial, concentration_ml_per_vial
            FROM inventory
            WHERE item_name = %s
              AND quantity > 0
              AND expiration_date IS NOT NULL
              AND expiration_date >= CURRENT_DATE
            ORDER BY expiration_date ASC
            LIMIT 1
        """, (record.drug_name,))

        new_inventory = cur.fetchone()

        if not new_inventory:
            raise HTTPException(
                status_code=404,
                detail="No eligible inventory lots found for updated medication."
            )

        new_ml_per_vial = new_inventory[0] or new_inventory[1]

        if not new_ml_per_vial:
            raise HTTPException(
                status_code=400,
                detail="Missing mL per vial for updated medication"
            )

        new_dose_ml = (
            float(record.dose) / 100
            if record.unit == "units"
            else float(record.dose)
        )

        required_quantity = (
            new_dose_ml / float(new_ml_per_vial)
        )

        # Calculate the updated inventory allocation using FEFO.
        new_allocations = allocate_inventory_fefo(
            cur,
            record.drug_name,
            required_quantity
        )

        # Deduct inventory from the selected FEFO lots.
        apply_fefo_allocations(
            cur,
            new_allocations
        )

        primary_lot = new_allocations[0]["lot_number"]

        # Update the injection record. The first FEFO-selected lot remains
        # in injection_history for compatibility with the existing schema,
        # while the allocation table stores the complete lot breakdown.
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
            primary_lot,
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

        # Record the new lot-by-lot allocation history.
        record_fefo_allocations(
            cur,
            injection_id,
            new_allocations
        )

        conn.commit()

        return {
            "message": "Injection updated successfully",
            "inventory_allocation": [
                {
                    "lot_number": allocation["lot_number"],
                    "quantity_used": allocation["quantity_used"],
                    "expiration_date": str(
                        allocation["expiration_date"]
                    )
                }
                for allocation in new_allocations
            ]
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

def delete_injection_by_id(injection_id: str):
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Confirm the injection exists and retrieve information needed
        # for backward compatibility with pre-FEFO injection records.
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

        # CS 499 Category Two Enhancement:
        # Restore the exact inventory allocations recorded by the FEFO
        # algorithm rather than assuming the injection used one lot.
        allocations = restore_fefo_allocations(
            cur,
            injection_id
        )

        if allocations:
            total_restored = sum(
                float(quantity_used)
                for _, quantity_used in allocations
            )

        else:
            # Backward compatibility:
            # Older injection records created before the FEFO enhancement
            # do not have allocation records, so use the original
            # single-lot restoration behavior.
            cur.execute("""
                SELECT ml_per_vial, concentration_ml_per_vial
                FROM inventory
                WHERE item_name = %s
                  AND lot_number = %s
            """, (
                drug_name,
                lot_number
            ))

            inventory_row = cur.fetchone()

            if not inventory_row:
                raise HTTPException(
                    status_code=404,
                    detail="Inventory item not found"
                )

            ml_per_vial = inventory_row[0] or inventory_row[1]

            if not ml_per_vial:
                raise HTTPException(
                    status_code=400,
                    detail="Missing mL per vial for inventory item"
                )

            dose_ml = (
                dose / 100
                if unit == "units"
                else dose
            )

            total_restored = dose_ml / float(ml_per_vial)

            cur.execute("""
                UPDATE inventory
                SET quantity = quantity + %s
                WHERE item_name = %s
                  AND lot_number = %s
            """, (
                total_restored,
                drug_name,
                lot_number
            ))

        # The allocation rows for FEFO injections are automatically
        # removed by ON DELETE CASCADE.
        cur.execute("""
            DELETE FROM injection_history
            WHERE injection_id = %s
        """, (injection_id,))

        conn.commit()

        return {
            "message": "Injection deleted successfully"
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
