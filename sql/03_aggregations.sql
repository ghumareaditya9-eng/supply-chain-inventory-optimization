-- ====================================================================
-- 03_aggregations.sql: Demand, Lead Time, and ABC Classification Queries
-- ====================================================================

-- 1. Weekly Demand by SKU
-- Formatted for SQLite with ANSI/Postgres equivalent syntax notes
-- (PostgreSQL equivalent: DATE_TRUNC('week', order_date))
DROP VIEW IF EXISTS v_weekly_demand_by_sku;
CREATE VIEW v_weekly_demand_by_sku AS
SELECT 
    sku_id,
    product_name,
    category,
    DATE(order_date, 'weekday 0', '-6 days') AS week_start,
    SUM(quantity) AS units_sold,
    SUM(line_total_revenue) AS weekly_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM cleaned_orders
GROUP BY sku_id, product_name, category, week_start
ORDER BY sku_id, week_start;

-- 2. Monthly Demand by SKU
-- (PostgreSQL equivalent: DATE_TRUNC('month', order_date))
DROP VIEW IF EXISTS v_monthly_demand_by_sku;
CREATE VIEW v_monthly_demand_by_sku AS
SELECT 
    sku_id,
    product_name,
    category,
    strftime('%Y-%m-01', order_date) AS month_start,
    SUM(quantity) AS units_sold,
    SUM(line_total_revenue) AS monthly_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM cleaned_orders
GROUP BY sku_id, product_name, category, month_start
ORDER BY sku_id, month_start;

-- 3. Supplier Lead Time Performance Metrics
DROP VIEW IF EXISTS v_supplier_performance;
CREATE VIEW v_supplier_performance AS
SELECT 
    supplier_id,
    COUNT(order_id) AS total_fulfillments,
    ROUND(AVG(lead_time_days), 2) AS avg_lead_time_days,
    ROUND(AVG(lead_time_days) / 7.0, 2) AS avg_lead_time_weeks,
    MIN(lead_time_days) AS min_lead_time_days,
    MAX(lead_time_days) AS max_lead_time_days
FROM cleaned_orders
GROUP BY supplier_id
ORDER BY total_fulfillments DESC;

-- 4. SKU Demand Variability & Statistical Profile
-- Computes average weekly demand, variance, standard deviation
DROP VIEW IF EXISTS v_sku_demand_variability;
CREATE VIEW v_sku_demand_variability AS
WITH sku_weekly_stats AS (
    SELECT 
        sku_id,
        product_name,
        category,
        AVG(units_sold) AS avg_weekly_demand,
        -- Standard deviation calculation: sqrt(avg(x^2) - avg(x)^2)
        SQRT(MAX(0.01, AVG(units_sold * units_sold) - AVG(units_sold) * AVG(units_sold))) AS stddev_weekly_demand,
        MIN(units_sold) AS min_weekly_demand,
        MAX(units_sold) AS max_weekly_demand,
        COUNT(week_start) AS active_weeks_count,
        SUM(units_sold) AS total_units_sold,
        SUM(weekly_revenue) AS total_revenue
    FROM v_weekly_demand_by_sku
    GROUP BY sku_id, product_name, category
)
SELECT 
    sku_id,
    product_name,
    category,
    ROUND(avg_weekly_demand, 2) AS avg_weekly_demand,
    ROUND(stddev_weekly_demand, 2) AS stddev_weekly_demand,
    -- Coefficient of Variation (CV = stddev / mean) - indicates demand stability
    ROUND(stddev_weekly_demand / NULLIF(avg_weekly_demand, 0), 3) AS coefficient_of_variation,
    min_weekly_demand,
    max_weekly_demand,
    active_weeks_count,
    total_units_sold,
    ROUND(total_revenue, 2) AS total_revenue
FROM sku_weekly_stats
ORDER BY total_revenue DESC;

-- 5. ABC Classification Query (Pareto 80/15/5 Segmentation)
DROP VIEW IF EXISTS v_sku_abc_classification;
CREATE VIEW v_sku_abc_classification AS
WITH sku_revenue AS (
    SELECT 
        sku_id,
        product_name,
        category,
        unit_price,
        unit_cost,
        supplier_id,
        SUM(line_total_revenue) AS total_revenue,
        SUM(quantity) AS total_units
    FROM cleaned_orders
    GROUP BY sku_id, product_name, category, unit_price, unit_cost, supplier_id
),
revenue_ranked AS (
    SELECT 
        sku_id,
        product_name,
        category,
        unit_price,
        unit_cost,
        supplier_id,
        total_revenue,
        total_units,
        SUM(total_revenue) OVER () AS grand_total_revenue,
        SUM(total_revenue) OVER (ORDER BY total_revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_cumulative_revenue
    FROM sku_revenue
)
SELECT 
    sku_id,
    product_name,
    category,
    unit_price,
    unit_cost,
    supplier_id,
    ROUND(total_revenue, 2) AS total_revenue,
    total_units,
    ROUND(running_cumulative_revenue / grand_total_revenue * 100.0, 2) AS cumulative_revenue_pct,
    CASE 
        WHEN (running_cumulative_revenue / grand_total_revenue) <= 0.80 THEN 'A'
        WHEN (running_cumulative_revenue / grand_total_revenue) <= 0.95 THEN 'B'
        ELSE 'C'
    END AS abc_category
FROM revenue_ranked
ORDER BY total_revenue DESC;
