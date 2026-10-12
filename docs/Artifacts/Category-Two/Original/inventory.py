import streamlit as st
import pandas as pd

from api.client import api_get, api_post, api_put, api_delete
from utils.helpers import render_page_header



def clear_inventory_action():
    st.session_state["inventory_action"] = None
    st.session_state["selected_inventory"] = None


def get_stock_status(quantity, reorder):
    quantity = float(quantity or 0)
    reorder = float(reorder or 0)

    if quantity <= reorder:
        return "Critical" if quantity <= reorder * 0.5 else "Low Stock"

    return "In Stock"


def render_inventory_detail_card(item):
    st.markdown(f"""
    <div class="inventory-detail-card">
        <div class="inventory-detail-title">{item.get("item_name")}</div>
        <div class="inventory-detail-subtitle">Lot: {item.get("lot_number")}</div>
        <br>
        <div><strong>Quantity:</strong> {item.get("quantity")} vials</div>
        <div><strong>mL per Vial:</strong> {item.get("ml_per_vial")}</div>
        <div><strong>mg/mL:</strong> {item.get("mg_per_ml") or "N/A"}</div>
        <div><strong>Reorder Level:</strong> {item.get("reorder_level")}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✏️ Edit", key=f"edit_{item['inventory_id']}"):
            st.session_state["inventory_action"] = "edit"
            st.session_state["selected_inventory"] = item
            st.rerun()

    with col2:
        if st.button("➕ Restock", key=f"restock_{item['inventory_id']}"):
            st.session_state["inventory_action"] = "restock"
            st.session_state["selected_inventory"] = item
            st.rerun()

    with col3:
        if st.button("🗑️ Delete", key=f"delete_{item['inventory_id']}"):
            st.session_state["inventory_action"] = "delete"
            st.session_state["selected_inventory"] = item
            st.rerun()

def render_add_inventory_form():
    st.markdown("### ➕ Add Inventory")

    STANDARD_MEDS = {
        "Testosterone Cyp": {"ml_per_vial": 30, "mg_per_ml": 200},
        "Semaglutide": {"ml_per_vial": 10, "mg_per_ml": None},
        "Tirzepatide": {"ml_per_vial": 8, "mg_per_ml": None},
        "Retatrutide": {"ml_per_vial": 5, "mg_per_ml": None},
        "Anastrozole": {
            "ml_per_vial": 1,   # ✅ safe default
            "mg_per_ml": None,
            "unit": "mg"
        }
    }

    item_name = st.selectbox(
        "Medication",
        list(STANDARD_MEDS.keys()),
        key="add_inventory_medication"
    )

    selected_med = STANDARD_MEDS[item_name]

    # -------------------------------
    # INFO DISPLAY (ONLY UI)
    # -------------------------------
    if selected_med.get("ml_per_vial"):
        st.info(f"Vial Size: {selected_med['ml_per_vial']} mL")

    if selected_med.get("mg_per_ml"):
        st.info(f"Concentration: {selected_med['mg_per_ml']} mg/mL")

    if selected_med.get("unit") == "mg":
        st.info("Unit-based medication (mg)")

    # -------------------------------
    # 🚨 FORM (ALWAYS RENDERS)
    # -------------------------------
    with st.form("add_inventory_form"):

        col1, col2 = st.columns(2)

        with col1:
            lot_number = st.text_input("Lot Number")
            quantity = st.number_input("Quantity", min_value=0.0, step=1.0)

        with col2:
            reorder_level = st.number_input("Reorder Level", min_value=0.0, step=1.0)

        col_save, col_cancel = st.columns(2)

        with col_save:
            submitted = st.form_submit_button("Save Item")

        with col_cancel:
            cancel = st.form_submit_button("Cancel")

        # -------------------------------
        # ACTION HANDLING (INSIDE FORM)
        # -------------------------------
        if cancel:
            clear_inventory_action()
            st.rerun()

        if submitted:
            if not lot_number.strip():
                st.error("Lot number is required ❌")
                return

            payload = {
                "item_name": item_name,
                "lot_number": lot_number.strip(),
                "quantity": quantity,
                "unit": selected_med.get("unit", "vials"),
                "reorder_level": reorder_level,
                "ml_per_vial": selected_med.get("ml_per_vial"),
                "mg_per_ml": selected_med.get("mg_per_ml"),
            }

            response, result = api_post("/add_inventory", payload)

            if response and response.status_code == 200 and "error" not in result:
                st.session_state["inventory_success"] = "Item added ✅"
                clear_inventory_action()
                st.rerun()
            else:
                st.error(result.get("error", "Failed to add inventory item"))

def render_edit_inventory_form(item):
    st.markdown("### ✏️ Edit Inventory")

    # -------------------------------
    # CONTEXT CARD (THIS IS THE FIX)
    # -------------------------------
    st.markdown(f"""
    <div style="
        background:#F8F6F2;
        border:1px solid #E5DED3;
        border-radius:14px;
        padding:14px;
        margin-bottom:16px;
    ">
    <strong>{item.get("item_name")}</strong><br>
    Lot: {item.get("lot_number")}<br>
    Current Quantity: {item.get("quantity")} vials
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------
    # FORM
    # -------------------------------
    with st.form(f"edit_inventory_form_{item['inventory_id']}"):
        col1, col2 = st.columns(2)

        with col1:
            qty = st.number_input(
                "Quantity",
                value=float(item.get("quantity", 0)),
                min_value=0.0,
                step=0.1
            )

        with col2:
            reorder = st.number_input(
                "Reorder Level",
                value=float(item.get("reorder_level", 0)),
                min_value=0.0,
                step=0.1
            )

        col_save, col_cancel = st.columns(2)

        with col_save:
            submitted = st.form_submit_button("Save Changes")

        with col_cancel:
            cancel = st.form_submit_button("Cancel")

    if cancel:
        clear_inventory_action()
        st.rerun()

    if submitted:
        payload = {
            "item_name": item["item_name"],
            "lot_number": item["lot_number"],
            "quantity": qty,
            "unit": item.get("unit", "vials"),
            "reorder_level": reorder,
            "ml_per_vial": item.get("ml_per_vial"),
            "mg_per_ml": item.get("mg_per_ml"),
        }

        response, result = api_put(
            f"/update_inventory/{item['inventory_id']}",
            payload
        )

        if response and response.status_code == 200 and "error" not in result:
            st.session_state["inventory_success"] = "Inventory updated ✅"
            clear_inventory_action()
            st.rerun()
        else:
            st.error(result.get("error", "Update failed"))


def render_restock_form(item):
    st.markdown("### ➕ Restock Inventory")

    # -------------------------------
    # CONTEXT CARD
    # -------------------------------
    st.markdown(f"""
    <div style="
        background:#F8F6F2;
        border:1px solid #E5DED3;
        border-radius:14px;
        padding:14px;
        margin-bottom:16px;
    ">
    <strong>{item.get("item_name")}</strong><br>
    Lot: {item.get("lot_number")}<br>
    Current Quantity: {item.get("quantity")} vials
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------
    # FORM
    # -------------------------------
    with st.form(f"restock_inventory_form_{item['inventory_id']}"):
        amount = st.number_input(
            "Add Quantity",
            min_value=1.0,
            step=1.0,
            value=1.0
        )

        col_save, col_cancel = st.columns(2)

        with col_save:
            submitted = st.form_submit_button("Apply Restock")

        with col_cancel:
            cancel = st.form_submit_button("Cancel")

    if cancel:
        clear_inventory_action()
        st.rerun()

    if submitted:
        new_quantity = float(item.get("quantity", 0)) + float(amount)

        payload = {
            "item_name": item["item_name"],
            "lot_number": item["lot_number"],
            "quantity": new_quantity,
            "unit": item.get("unit", "vials"),
            "reorder_level": item.get("reorder_level", 0),
            "ml_per_vial": item.get("ml_per_vial"),
            "mg_per_ml": item.get("mg_per_ml"),
        }

        response, result = api_put(
            f"/update_inventory/{item['inventory_id']}",
            payload
        )

        if response and response.status_code == 200 and "error" not in result:
            st.session_state["inventory_success"] = f"Added {amount:g} vial(s) ✅"
            clear_inventory_action()
            st.rerun()
        else:
            st.error(result.get("error", "Restock failed"))


def render_delete_inventory(item):
    st.markdown("### 🗑️ Delete Inventory")

    # -------------------------------
    # CONTEXT CARD
    # -------------------------------
    st.markdown(f"""
    <div style="
        background:#FFF4EE;
        border:1px solid #F0C8B7;
        border-radius:14px;
        padding:14px;
        margin-bottom:16px;
    ">
    <strong>{item.get("item_name")}</strong><br>
    Lot: {item.get("lot_number")}<br>
    Quantity: {item.get("quantity")} vials
    </div>
    """, unsafe_allow_html=True)

    st.warning("This action cannot be undone.")

    col_confirm, col_cancel = st.columns(2)

    with col_confirm:
        if st.button("Confirm Delete", key=f"confirm_delete_{item['inventory_id']}"):
            response, result = api_delete(
                f"/delete_inventory/{item['inventory_id']}"
            )

            if response and response.status_code == 200 and "error" not in result:
                st.session_state["inventory_success"] = "Item deleted 🗑️"
                clear_inventory_action()
                st.rerun()
            else:
                st.error(result.get("error", "Delete failed"))

    with col_cancel:
        if st.button("Cancel", key=f"cancel_delete_{item['inventory_id']}"):
            clear_inventory_action()
            st.rerun()


def render_inventory_table(filtered_data):
    st.markdown("## Inventory Records")

    if not filtered_data:
        st.info("No matching inventory items found.")
        return

    table_rows = []

    for item in filtered_data:
        status = get_stock_status(
            item.get("quantity", 0),
            item.get("reorder_level", 0)
        )

        table_rows.append({
            "Item Name": item.get("item_name"),
            "Lot Number": item.get("lot_number"),
            "Quantity": item.get("quantity"),
            "Unit": item.get("unit"),
            "mL per Vial": item.get("ml_per_vial"),
            "mg/mL": item.get("mg_per_ml"),
            "Reorder Level": item.get("reorder_level"),
            "Status": status,
        })

    df = pd.DataFrame(table_rows)

    def highlight_low_stock(row):
        return [
            "background-color: #FFF5F2"
            if row["Status"] in ["Low Stock", "Critical"]
            else ""
            for _ in row
        ]

    def status_color(val):
        if val == "Critical":
            return "color: #B71C1C; font-weight: 800;"
        if val == "Low Stock":
            return "color: #C65A2E; font-weight: 700;"
        return "color: #2E7D32; font-weight: 700;"

    styled_df = (
        df.style
        .apply(highlight_low_stock, axis=1)
        .map(status_color, subset=["Status"])
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )


def inventory_page():
    render_page_header(
        "Inventory Management",
        "Track clinic supplies, monitor stock, and manage reorder levels",
    )

    st.session_state.setdefault("inventory_action", None)
    st.session_state.setdefault("selected_inventory", None)

    if "inventory_success" in st.session_state:
        st.toast(st.session_state["inventory_success"])
        del st.session_state["inventory_success"]

    action = st.session_state.get("inventory_action")
    selected_item = st.session_state.get("selected_inventory")

    # -------------------------------
    # EXCLUSIVE ACTION MODES
    # -------------------------------
    if action == "add":
        render_add_inventory_form()
        return

    if action == "edit" and selected_item:
        render_edit_inventory_form(selected_item)
        return

    if action == "restock" and selected_item:
        render_restock_form(selected_item)
        return

    if action == "delete" and selected_item:
        render_delete_inventory(selected_item)
        return

    # -------------------------------
    # NORMAL PAGE MODE
    # -------------------------------
    data = api_get("/inventory", default=[])

    low_items = [
        item for item in data
        if float(item.get("quantity", 0)) <= float(item.get("reorder_level", 0))
    ]

    if low_items:
        st.markdown("### ⚠️ Inventory Alerts")

        for item in low_items:
            quantity = float(item.get("quantity", 0))
            reorder = float(item.get("reorder_level", 0))

            if quantity <= reorder * 0.5:
                st.error(
                    f"🚨 CRITICAL: {item['item_name']} "
                    f"(Lot {item.get('lot_number')})"
                )
            else:
                st.warning(
                    f"⚠️ Low Stock: {item['item_name']} "
                    f"(Lot {item.get('lot_number')})"
                )

    total_items = len(data)
    low_stock_count = len(low_items)
    total_vials = sum(float(item.get("quantity", 0)) for item in data)

    stat1, stat2, stat3 = st.columns(3)

    with stat1:
        st.markdown(f"""
        <div class="inventory-stat-card">
            <div class="inventory-stat-label">Total Items</div>
            <div class="inventory-stat-value">{total_items}</div>
        </div>
        """, unsafe_allow_html=True)

    with stat2:
        st.markdown(f"""
        <div class="inventory-stat-card">
            <div class="inventory-stat-label">Low Stock</div>
            <div class="inventory-stat-value">{low_stock_count}</div>
        </div>
        """, unsafe_allow_html=True)

    with stat3:
        st.markdown(f"""
        <div class="inventory-stat-card">
            <div class="inventory-stat-label">Total Vials</div>
            <div class="inventory-stat-value">{total_vials:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    toolbar_col1, toolbar_col2, toolbar_col3 = st.columns([2, 1, 1])

    with toolbar_col1:
        search_term = st.text_input(
            "Search Inventory",
            placeholder="Search by medication or lot number"
        )

    with toolbar_col2:
        stock_filter = st.selectbox(
            "Stock Status",
            ["All", "In Stock", "Low Stock", "Critical"]
        )

    with toolbar_col3:
        sort_by = st.selectbox(
            "Sort By",
            ["Item Name", "Quantity", "Reorder Level"]
        )

    filtered_data = []

    for item in data:
        item_name = str(item.get("item_name", "")).lower()
        lot_number = str(item.get("lot_number", "")).lower()
        quantity = float(item.get("quantity", 0))
        reorder = float(item.get("reorder_level", 0))
        status = get_stock_status(quantity, reorder)

        matches_search = (
            search_term.lower() in item_name
            or search_term.lower() in lot_number
        ) if search_term else True

        matches_filter = (
            stock_filter == "All"
            or stock_filter == status
            or (
                stock_filter == "Low Stock"
                and status in ["Low Stock", "Critical"]
            )
        )

        if matches_search and matches_filter:
            new_item = item.copy()
            new_item["_status"] = status
            filtered_data.append(new_item)

    if sort_by == "Item Name":
        filtered_data.sort(key=lambda x: str(x.get("item_name", "")).lower())
    elif sort_by == "Quantity":
        filtered_data.sort(key=lambda x: float(x.get("quantity", 0)))
    elif sort_by == "Reorder Level":
        filtered_data.sort(key=lambda x: float(x.get("reorder_level", 0)))

    render_inventory_table(filtered_data)

    st.markdown("## Manage Your Inventory")

    if st.button("➕ Add New Inventory Item", key="open_add_inventory"):
        st.session_state["inventory_action"] = "add"
        st.session_state["selected_inventory"] = None
        st.rerun()

    if not filtered_data:
        st.info("No inventory item available to manage.")
        return

    inventory_options = {
        f"{item['item_name']} ({item.get('lot_number', 'No Lot')})": item
        for item in filtered_data
    }

    selected_label = st.selectbox(
        "Select Inventory Item",
        ["Select an inventory item..."] + list(inventory_options.keys()),
        key="inventory_item_selector"
    )

    if selected_label != "Select an inventory item...":
        st.session_state["selected_inventory"] = inventory_options[selected_label]
        selected_item = st.session_state["selected_inventory"]
        render_inventory_detail_card(selected_item)
    else:
        st.markdown("""
        <div class="empty-state-card">
            <div class="empty-state-title">No Item Selected</div>
            <div class="empty-state-text">
                Select an inventory item above to manage it.
            </div>
        </div>
        """, unsafe_allow_html=True)
