-- ====================================================================
-- 02_cleaning.sql: Data Sanitization, Deduplication, & Integrity Rules
-- ====================================================================

-- Step 1: Clear cleaned_orders prior to ingestion
DELETE FROM cleaned_orders;

-- Step 2: Insert validated, deduplicated, and typed records from raw_orders
WITH ranked_orders AS (
    SELECT 
        order_id,
        order_date,
        customer_id,
        sku_id,
        product_name,
        category,
        unit_price,
        unit_cost,
        quantity,
        supplier_id,
        supplier_lead_time_days,
        order_cost,
        holding_cost_annual_rate,
        ROW_NUMBER() OVER (
            PARTITION BY order_id, sku_id 
            ORDER BY raw_id ASC
        ) as row_num
    FROM raw_orders
    WHERE 
        order_id IS NOT NULL 
        AND TRIM(order_id) != ''
        AND sku_id IS NOT NULL 
        AND TRIM(sku_id) != ''
        AND order_date IS NOT NULL
        AND quantity IS NOT NULL
        AND unit_price IS NOT NULL
        AND unit_cost IS NOT NULL
),
sanitized_records AS (
    SELECT
        TRIM(order_id) AS order_id,
        -- Normalize dates to YYYY-MM-DD
        DATE(SUBSTR(TRIM(order_date), 1, 10)) AS order_date,
        TRIM(customer_id) AS customer_id,
        TRIM(sku_id) AS sku_id,
        TRIM(product_name) AS product_name,
        TRIM(category) AS category,
        CAST(unit_price AS NUMERIC(10,2)) AS unit_price,
        CAST(unit_cost AS NUMERIC(10,2)) AS unit_cost,
        CAST(quantity AS INTEGER) AS quantity,
        TRIM(supplier_id) AS supplier_id,
        CAST(supplier_lead_time_days AS INTEGER) AS lead_time_days,
        COALESCE(CAST(order_cost AS NUMERIC(10,2)), 75.00) AS order_cost,
        COALESCE(CAST(holding_cost_annual_rate AS NUMERIC(6,4)), 0.22) AS holding_cost_annual_rate
    FROM ranked_orders
    WHERE 
        row_num = 1 -- Eliminate duplicate transactions
)
INSERT INTO cleaned_orders (
    order_id,
    order_date,
    customer_id,
    sku_id,
    product_name,
    category,
    unit_price,
    unit_cost,
    quantity,
    line_total_revenue,
    line_total_cost,
    supplier_id,
    lead_time_days,
    order_cost,
    holding_cost_annual_rate
)
SELECT 
    order_id,
    order_date,
    customer_id,
    sku_id,
    product_name,
    category,
    unit_price,
    unit_cost,
    quantity,
    ROUND(quantity * unit_price, 2) AS line_total_revenue,
    ROUND(quantity * unit_cost, 2) AS line_total_cost,
    supplier_id,
    lead_time_days,
    order_cost,
    holding_cost_annual_rate
FROM sanitized_records
WHERE 
    quantity > 0                    -- Filter returns / negative test artifacts
    AND unit_price > 0              -- Filter zero/negative pricing errors
    AND unit_cost > 0               -- Filter cost inaccuracies
    AND lead_time_days > 0          -- Filter impossible zero lead times
    AND order_date IS NOT NULL;

-- Step 3: Sanity check counts and anomaly reporting
-- Output total clean rows processed
SELECT 
    (SELECT COUNT(*) FROM raw_orders) AS total_raw_records,
    (SELECT COUNT(*) FROM cleaned_orders) AS total_cleaned_records,
    (SELECT COUNT(*) FROM raw_orders) - (SELECT COUNT(*) FROM cleaned_orders) AS filtered_records_count;
