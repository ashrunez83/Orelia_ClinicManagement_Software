-- CS 499 Category Three: Database Enhancement
-- Orelia Clinic Management Software
--
-- These database enhancements improve query performance, data integrity,
-- and scalability based on the application's existing database operations.


-- ============================================================
-- 1. FEFO Inventory Query Index
-- ============================================================
-- Supports FEFO inventory queries by indexing medication name and
-- expiration date, allowing PostgreSQL to more efficiently locate
-- eligible inventory lots in expiration-date order.

CREATE INDEX idx_inventory_item_expiration
ON inventory (item_name, expiration_date);


-- ============================================================
-- 2. Injection History Index
-- ============================================================
-- Supports injection history retrieval by indexing injection dates,
-- improving performance when records are returned in chronological order.

CREATE INDEX idx_injection_history_date
ON injection_history (injection_date DESC);


-- ============================================================
-- 3. Injection Allocation Lookup Index
-- ============================================================
-- Supports efficient retrieval of inventory allocations associated
-- with an injection during update, deletion, and inventory restoration.

CREATE INDEX idx_injection_allocations_injection_id
ON injection_inventory_allocations (injection_id);


-- ============================================================
-- 4. Inventory Quantity Integrity Constraint
-- ============================================================
-- Enforces inventory integrity at the database level by preventing
-- inventory quantities from being stored as negative values.

ALTER TABLE inventory
ADD CONSTRAINT chk_inventory_quantity_nonnegative
CHECK (quantity >= 0);
