# Power BI Dashboard: Complete Step-by-Step Construction Guide

This guide walks you through building an executive-ready **Supply Chain Demand Forecasting & Inventory Optimization Dashboard** in **Microsoft Power BI Desktop**.

---

## 1. Overview of the Dashboard Architecture

The dashboard is structured into **3 interactive executive report pages**:

```
[ Power BI Report: Supply Chain Analytics ]
│
├── Page 1: Executive Inventory Health & Risk Overview (KPIs, At-Risk Revenue, Priority POs)
├── Page 2: Demand Forecasting & Trend Analytics (Actuals vs Predictions, 80% CI Bands)
└── Page 3: Supplier Lead Time & Pareto ABC Matrix (Vendor Delivery Performance & Revenue Share)
```

---

## 2. Step-by-Step Build Instructions

### Step 1: Ingest Data Tables into Power BI Desktop
1. Open **Power BI Desktop**.
2. Click **Get Data** > **Text/CSV**.
3. Navigate to your project folder: `C:\Users\adity\project\supply-chain-inventory-optimization\`.
4. Import the following 4 files one by one (click **Load** for each):
   * `outputs/reorder_recommendations.csv`
   * `outputs/forecast_results.csv`
   * `data/processed/sku_abc_classification.csv`
   * `data/processed/supplier_performance.csv`

---

### Step 2: Establish the Data Model Relationships (Star Schema)
1. On the left sidebar, click the **Model View** icon (the 3 connected boxes).
2. Ensure relationships are linked as follows:
   * Drag `sku_abc_classification[sku_id]` $\longrightarrow$ `reorder_recommendations[sku_id]` *(1-to-many)*
   * Drag `sku_abc_classification[sku_id]` $\longrightarrow$ `forecast_results[sku_id]` *(1-to-many)*
   * Drag `supplier_performance[supplier_id]` $\longrightarrow$ `reorder_recommendations[supplier_id]` *(1-to-many)*

---

### Step 3: Create the DAX Measures Table
1. In the **Home** tab, click **Enter Data**.
2. Name the table `_Measures` and click **Load**.
3. Right-click `_Measures` > **New Measure**, and paste the DAX formulas from [`dashboard/powerbi/DAX_Measures.dax`](DAX_Measures.dax):
   * `Total Revenue at Risk = SUM('reorder_recommendations'[revenue_at_risk])`
   * `High Risk SKU Count = CALCULATE(COUNTROWS('reorder_recommendations'), 'reorder_recommendations'[risk_status] = "HIGH RISK")`
   * `Total Recommended Order Units = SUM('reorder_recommendations'[recommended_order_qty])`
   * `Average Model MAPE = AVERAGE('reorder_recommendations'[test_mape_pct])`
   * `Risk Status Color = SWITCH(SELECTEDVALUE('reorder_recommendations'[risk_status]), "HIGH RISK", "#E74C3C", "MEDIUM RISK", "#F39C12", "HEALTHY", "#2ECC71", "#95A5A6")`

---

### Step 4: Build Page 1 — Executive Inventory Health & Risk Overview
*Rename Page 1 to **"Executive Overview"**.*

1. **Top KPI Cards (Add 4 Card Visuals horizontally):**
   * **Card 1:** Field = `[Total Revenue at Risk]` $\rightarrow$ Format as Currency (`$211.7K`), Color = Dark Red (`#C0392B`).
   * **Card 2:** Field = `[High Risk SKU Count]` $\rightarrow$ Title = *"SKUs in Stockout Deficit"*, Value = `8 of 20`.
   * **Card 3:** Field = `[Total Recommended Order Units]` $\rightarrow$ Title = *"Recommended Replenishment"*, Value = `1,461 Units`.
   * **Card 4:** Field = `[Average Model MAPE]` $\rightarrow$ Format as Percentage (`18.76%`), Title = *"Forecast Model Accuracy"*.

2. **Top-Right Slicers:**
   * Add a Slicer visual for `reorder_recommendations[category]`.
   * Add a Slicer visual for `reorder_recommendations[risk_status]`.

3. **Middle-Left Visual: Horizontal Bar Chart (Revenue Exposure by Category)**
   * **Visual Type:** Clustered Bar Chart.
   * **Y-Axis:** `reorder_recommendations[category]`.
   * **X-Axis:** `[Total Revenue at Risk]`.
   * **Data Colors:** Red (`#E74C3C`).
   * *Insight:* Instantly shows that Consumer Electronics and Office & Productivity represent over 75% of stockout risk.

4. **Middle-Right Visual: Donut Chart (Stockout Risk Distribution)**
   * **Visual Type:** Donut Chart.
   * **Legend:** `reorder_recommendations[risk_status]`.
   * **Values:** `[Total Active SKUs]`.
   * **Colors:** High Risk = Red (`#E74C3C`), Healthy = Green (`#2ECC71`).

5. **Bottom Visual: Priority Purchase Order Table**
   * **Visual Type:** Table.
   * **Columns:** `sku_id`, `product_name`, `category`, `current_stock`, `reorder_point`, `safety_stock`, `units_at_risk`, `revenue_at_risk`, `recommended_order_qty`.
   * **Conditional Formatting:**
     * Select `risk_status` or `revenue_at_risk` > **Conditional Formatting** > **Background color** > Format by **Field Value** > Choose `[Risk Status Color]`.

---

### Step 5: Build Page 2 — Demand Forecasting & Trend Analytics
*Click the `+` icon to add a new page, rename to **"Demand Forecasting"**.*

1. **Top Slicer:**
   * Add a Slicer for `forecast_results[product_name]` (Set to single-select dropdown).

2. **Main Center Visual: Time-Series Line Chart (Historical Actuals vs. 13-Week Forecast)**
   * **Visual Type:** Line Chart.
   * **X-Axis:** `forecast_results[week_start]`.
   * **Y-Axis:** 
     * `forecast_results[actual_demand]` (Line color = Slate Gray / Black).
     * `forecast_results[model_forecast]` (Line color = Corporate Blue `#1F4E79`).
     * `forecast_results[upper_bound_80pct]` (Dotted line).
     * `forecast_results[lower_bound_80pct]` (Dotted line).
   * *Insight:* Demonstrates how the model captures holiday spikes in Q4 and smooths out stochastic noise.

3. **Right KPI / Gauge Visual:**
   * Add a Gauge visual for `[Average Model MAPE]`. Target goal line set to `20%`. Value displays `18.76%` (Green).

---

### Step 6: Build Page 3 — Supplier Performance & Pareto ABC Matrix
*Add a new page, rename to **"Supplier & ABC Analysis"**.*

1. **Top Visual: Dual-Axis Pareto Revenue Chart**
   * **Visual Type:** Line and Clustered Column Chart.
   * **Shared X-Axis:** `sku_abc_classification[product_name]`.
   * **Column Y-Axis:** `sku_abc_classification[total_revenue]`.
   * **Line Y-Axis:** `sku_abc_classification[cumulative_revenue_pct]`.
   * *Insight:* Visually proves why Class A items generate 76.4% of catalog sales.

2. **Bottom Visual: Scatter Plot (Lead Time vs. Demand Volatility)**
   * **Visual Type:** Scatter Chart.
   * **X-Axis:** `reorder_recommendations[lead_time_days]`.
   * **Y-Axis:** `reorder_recommendations[demand_stddev_weekly]`.
   * **Bubble Size:** `reorder_recommendations[unit_price]`.
   * **Legend:** `reorder_recommendations[supplier_id]`.
   * *Insight:* Items in the top-right quadrant (long lead times + high volatility) require the highest safety stock cushions.

---

## 3. Executive Insights to Present to Interviewers

When presenting your Power BI dashboard in an interview, walk through these **3 data-driven business insights**:

1. **Insight 1: The High-Exposure Bottleneck ($211.7K at risk):**
   * *"Looking at our Executive Overview page, 8 of our top 20 items are currently below their Reorder Point. 3 products alone (`SKU-004` Standing Desk, `SKU-001` Headphones, and `SKU-011` Keyboard) account for **$142,000 (67%)** of our total revenue exposure."*
2. **Insight 2: The Overseas Supplier Risk (`SUP-104`):**
   * *"On Page 3, our scatter plot reveals that `SKU-011` has both high demand variance ($\sigma = 38.6$) and our longest supplier lead time (28 days from Shenzhen). This drives a massive Reorder Point of 649 units. We recommend a split shipment (air-freight 100 units immediately to survive the 4-week transit period)."*
3. **Insight 3: Capital Optimization via EOQ:**
   * *"Instead of ordering arbitrary round numbers, our dashboard recommends ordering exactly **1,461 units** distributed across the 8 deficit SKUs, balancing annual ordering fees against warehouse carrying costs."*
