# CS 499 Enhancement:
# Separates payment API endpoints from the original monolithic application
# while preserving transaction management and using centralized handling
# for unexpected errors.

import uuid

from fastapi import APIRouter

from database import get_db_connection, execute_query
from models.payment import PaymentModel

router = APIRouter()

@router.post("/add_payment")
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
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@router.get("/payments")
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

@router.put("/update_payment/{payment_id}")
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
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@router.delete("/delete_payment/{payment_id}")
def delete_payment(payment_id: str):
        execute_query("""
            DELETE FROM payments
            WHERE payment_id = %s
        """, (payment_id,), fetch=False)

        return {"message": "Payment deleted"}

