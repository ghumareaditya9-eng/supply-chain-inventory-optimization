-- ====================================================================
-- 01_schema.sql: Supply Chain Inventory Optimization Schema Definition
-- Supports SQLite and PostgreSQL syntax conventions
-- ====================================================================

-- Drop dependent views first to prevent schema locking
DROP VIEW IF EXISTS v_weekly_demand_by_sku;
DROP VIEW IF EXISTS v_monthly_demand_by_sku;
DROP VIEW IF EXISTS v_supplier_performance;
DROP VIEW IF EXISTS v_sku_demand_variability;
DROP VIEW IF EXISTS v_sku_abc_classification;

-- 1. Raw Orders Table (Staging table for untrusted raw ingest)
DROP TABLE IF EXISTS raw_orders;
CREATE TABLE raw_orders (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(50),
    order_date VARCHAR(50),
    customer_id VARCHAR(50),
    sku_id VARCHAR(50),
    product_name VARCHAR(255),
    category VARCHAR(100),
    unit_price NUMERIC(10, 2),
    unit_cost NUMERIC(10, 2),
    quantity VARCHAR(20),
    supplier_id VARCHAR(50),
    supplier_lead_time_days VARCHAR(20),
    order_cost NUMERIC(10, 2),
    holding_cost_annual_rate NUMERIC(6, 4)
);

CREATE INDEX IF NOT EXISTS idx_raw_order_sku ON raw_orders(order_id, sku_id);

-- 2. Cleaned Orders Table (Target sanitized transactional table)
DROP TABLE IF EXISTS cleaned_orders;
CREATE TABLE cleaned_orders (
    order_id VARCHAR(50) NOT NULL,
    order_date DATE NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    sku_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    unit_cost NUMERIC(10, 2) NOT NULL CHECK (unit_cost > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    line_total_revenue NUMERIC(12, 2) NOT NULL,
    line_total_cost NUMERIC(12, 2) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days > 0),
    order_cost NUMERIC(10, 2) NOT NULL,
    holding_cost_annual_rate NUMERIC(6, 4) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cleaned_sku_date ON cleaned_orders(sku_id, order_date);
CREATE INDEX IF NOT EXISTS idx_cleaned_supplier ON cleaned_orders(supplier_id);

-- 3. Warehouse On-Hand Inventory Table (Current stock levels)
DROP TABLE IF EXISTS inventory_master;
CREATE TABLE inventory_master (
    sku_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    current_stock INTEGER NOT NULL CHECK (current_stock >= 0),
    unit_price NUMERIC(10, 2) NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    holding_cost_annual_rate NUMERIC(6, 4) NOT NULL,
    order_cost NUMERIC(10, 2) NOT NULL
);
