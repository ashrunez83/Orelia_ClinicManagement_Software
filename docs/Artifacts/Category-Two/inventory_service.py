# CS 499 Category Two Enhancement:
# Extends inventory data operations to store and retrieve expiration dates,
# providing the data required by the FEFO inventory allocation algorithm.

from database import execute_query
from models.inventory import InventoryItem

def update_inventory_by_id(inventory_id: str, item: InventoryItem) :
    execute_query("""
        UPDATE inventory
        SET item_name=%s,
            lot_number=%s,
            quantity=%s,
            unit=%s,
            reorder_level=%s,
            ml_per_vial=%s,
            mg_per_ml=%s
            expiration_date=%s
        WHERE inventory_id=%s
    """, (
        item.item_name,
        item.lot_number,
        item.quantity,
        item.unit,
        item.reorder_level,
        item.ml_per_vial,
        item.mg_per_ml,
        item.expiration_date,
        inventory_id
    ), fetch=False)

    return {"message": "Inventory updated"}


def get_all_inventory():
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
            mg_per_ml,
            expiration_date
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
            "expiration_date": str(r[10]) if r[10] else None,
        }
        for r in rows
    ]


def create_inventory_item(item: InventoryItem):
    execute_query("""
        INSERT INTO inventory (
            item_name,
            lot_number,
            quantity,
            unit,
            reorder_level,
            concentration_ml_per_vial,
            ml_per_vial,
            mg_per_ml,
            expiration_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        item.item_name,
        item.lot_number,
        item.quantity,
        item.unit,
        item.reorder_level,
        item.ml_per_vial,
        item.ml_per_vial,
        item.mg_per_ml,
        item.expiration_date
    ), fetch=False)

    return {"message": "Inventory added"}


def delete_inventory_by_id(inventory_id: str):
    execute_query("""
        DELETE FROM inventory
        WHERE inventory_id=%s
    """, (inventory_id,), fetch=False)

    return {"message": "Deleted"}
