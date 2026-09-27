# CS 499 Enhancement:
# Separates inventory API endpoints from the original monolithic application
# and delegates inventory database operations to a dedicated service layer
# for improved separation of concerns and maintainability.


from fastapi import APIRouter

from models.inventory import InventoryItem
from services.inventory_service import (
    update_inventory_by_id,
    get_all_inventory,
    create_inventory_item,
    delete_inventory_by_id,
)

router = APIRouter()



@router.put("/update_inventory/{inventory_id}")
def update_inventory(inventory_id: str, item: InventoryItem):
       return update_inventory_by_id(inventory_id, item)
   

@router.get("/inventory")
def get_inventory():
   return get_all_inventory()

@router.post("/add_inventory")
def add_inventory(item: InventoryItem):
        return create_inventory_item(item)
   


@router.delete("/delete_inventory/{inventory_id}")
def delete_inventory(inventory_id: str):
        return delete_inventory_by_id(inventory_id)
   