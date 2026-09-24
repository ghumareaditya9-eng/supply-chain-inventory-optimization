# Supply Chain Demand Forecasting & Inventory Optimization

> ### Core Business Question:
> **"For our top 20 SKUs by revenue, what should the reorder point and safety stock be for the next quarter, given demand variability and current supplier lead times — and which SKUs are at highest stockout risk?"**

---

## 1. Executive Summary & Mini Case Study

| Metric | Business Impact |
| :--- | :--- |
| **Catalog Scope** | 50 SKUs across 5 retail categories over 104 weeks (2-year history) |
| **Focus Segment (Pareto Class A)** | Top 20 SKUs generating **76.4%** of total business revenue |
| **Forecasting Model Accuracy** | **18.76% Average MAPE** across top 20 items (12-week holdout test) |
| **Identified High-Risk Items** | **8 of 20 SKUs (40%)** currently below calculated Reorder Point |
| **Total Immediate Revenue at Risk** | **$211,727.80** exposed to stockouts during supplier lead times |
| **Action Plan** | Immediate purchase order placement for **1,461 units** ($120k working capital) |

An enterprise omni-channel retailer faced stockouts on high-velocity revenue drivers alongside surplus holding costs on slow-moving inventory. This project delivers an automated, end-to-end data pipeline combining **SQL sanitization**, **time-series demand forecasting**, and **classical operations research inventory models** (Safety Stock, Reorder Point, and Economic Order Quantity) to optimize working capital while sustaining a **95% cycle service level**.

---

## 2. Project Architecture & Directory Structure

```
supply-chain-inventory-optimization/
│
├── data/
│   ├── raw/                             # Original transactional dataset & inventory master
│   │   ├── supply_chain_raw.csv         # 20,949 raw transaction records (contains anomalies)
│   │   └── inventory_master.csv         # Warehouse on-hand stock & holding parameters
│   ├── processed/                       # Cleaned data and analytical views exported from SQL
│   │   ├── cleaned_orders.csv           # 20,794 sanitized orders
│   │   ├── weekly_demand.csv            # 5,200 SKU-week aggregated demand records
│   │   ├── monthly_demand.csv           # 1,200 SKU-month aggregated records
│   │   ├── supplier_performance.csv     # Vendor lead time means and standard deviations
│   │   ├── sku_demand_variability.csv   # Historical demand mean, stddev, and CV
│   │   └── sku_abc_classification.csv   # Pareto revenue rankings and ABC segments
│   └── supply_chain.db                  # SQLite database engine
│
├── sql/
│   ├── 01_schema.sql                    # DDL table creation with integrity constraints & indexes
│   ├── 02_cleaning.sql                  # Window function deduplication, type casting, null filtering
│   └── 03_aggregations.sql              # Weekly/monthly demand, vendor lead times, ABC segmentation
│
├── notebooks/
│   ├── 01_eda.ipynb                     # Exploratory analysis, seasonality spikes, Pareto curve
│   ├── 02_forecasting.ipynb             # Time-series trend + seasonality, 12-wk holdout, MAPE/RMSE
│   └── 03_inventory_optimization.ipynb  # Mathematical SS, ROP, EOQ, stockout revenue exposure
│
├── dashboard/
│   └── inventory_dashboard.xlsx         # Multi-tab executive Excel workbook with conditional formatting
│
├── outputs/
│   ├── forecast_results.csv             # Historical actuals, fitted values, and 13-week Q1-2025 forecasts
│   └── reorder_recommendations.csv      # Complete SKU decision matrix with risk flags and order quantities
│
├── scripts/
│   ├── generate_data.py                 # Synthetic data engine (DataCo / Store Item Demand schema)
│   ├── run_sql_pipeline.py              # Executes SQL lifecycle and exports processed CSVs
│   ├── run_optimization_pipeline.py     # Executes forecasting, OR formulas, and builds Excel workbook
│   ├── create_notebooks.py              # Builds clean Jupyter notebooks
│   └── execute_notebooks.py             # Verifies top-to-bottom notebook execution reproducibility
│
├── run_pipeline.py                      # Master pipeline entrypoint (single-command execution)
├── requirements.txt                     # Python dependencies
├── .gitignore                           # Repository hygiene
└── README.md                            # Executive case study & documentation
```

---

## 3. Data & Methodology

### Data Pipeline & SQL Sanitization
1. **Raw Ingestion & Schema:** 20,949 date-stamped transactions were staged in `raw_orders`. Deliberate anomalies were injected (duplicate order rows, missing foreign keys, negative quantities from return artifacts, zero prices).
2. **SQL Sanitization (`sql/02_cleaning.sql`):**
   - Employed `ROW_NUMBER() OVER (PARTITION BY order_id, sku_id ORDER BY raw_id ASC)` to remove 150 duplicate lines without loss of legitimate orders.
   - Filtered out records with non-positive quantities, pricing anomalies, and missing keys.
   - Standardized date types and computed line revenues and costs into `cleaned_orders` (20,794 valid records retained).
3. **Analytical Aggregations (`sql/03_aggregations.sql`):**
   - Derived weekly demand per SKU (`DATE(order_date, 'weekday 0', '-6 days')`).
   - Evaluated vendor fulfillment performance (lead time means and variances across 8 suppliers).
   - Executed **Pareto ABC Segmentation** using cumulative revenue window functions.

### Demand Forecasting Engine
- **Train / Test Split:** Held out the final 12 weeks (~1 quarter) of historical demand for out-of-sample validation across all top 20 SKUs.
- **Decomposition Model:** Additive time-series regression capturing linear growth trends and 52-week annual Fourier harmonics:
  $$y(t) = \alpha + \beta \cdot t + \sum_{k=1}^{2} \left[ A_k \sin\left(\frac{2\pi k t}{52}\right) + B_k \cos\left(\frac{2\pi k t}{52}\right) \right] + \epsilon(t)$$
- **Model Evaluation:** Benchmarked against test actuals, achieving a mean **MAPE of 18.76%** and **RMSE of 21.88 units**, confirming solid generalization over volatile retail trends.
- **Horizon:** Retrained on full 104-week history to generate 13-week ahead forecasts (Q1-2025) with 80% confidence intervals.

### Mathematical Inventory Optimization
To balance inventory availability against working capital, standard industrial operations research formulas were implemented:

1. **Safety Stock ($SS$):**
   $$SS = Z \times \sigma_{\text{demand}} \times \sqrt{L_{\text{weeks}}}$$
   - $Z = 1.65$ (95% cycle service level).
   - $\sigma_{\text{demand}}$: Standard deviation of weekly demand.
   - $L_{\text{weeks}}$: Vendor replenishment lead time ($\text{days} / 7$).

2. **Reorder Point ($ROP$):**
   $$ROP = (\bar{d}_{\text{forecast}} \times L_{\text{weeks}}) + SS$$
   Triggers purchase requisition when on-hand stock falls below expected lead time demand plus safety buffer.

3. **Economic Order Quantity ($EOQ$):**
   $$EOQ = \sqrt{\frac{2 \times D_{\text{annual}} \times S}{H}}$$
   - $D_{\text{annual}}$: Annualized forecast demand ($\bar{d}_{\text{forecast}} \times 52$).
   - $S$: Fixed purchase order administration cost ($50 - $140 per PO).
   - $H = \text{holding\_rate} \times \text{unit\_cost}$: Annual inventory carrying cost ($18\% - 24\%$ of item cost).

---

## 4. Key Findings

* **Finding 1: High Stockout Risk on Critical Revenue Generators**
  **8 of our top 20 SKUs (40%)** have current warehouse inventory below their calculated Reorder Point. If not replenished immediately, stockouts will occur before supplier shipments arrive.
* **Finding 2: $211,727.80 Immediate Revenue Exposure**
  The top 3 stockout exposure items account for **$142,019.57 (67%)** of total at-risk revenue:
  1. `SKU-004` (Dual-Motor Electric Standing Desk): **$47,904.00** at risk (96 unit deficit, lead time 18 days).
  2. `SKU-001` (Pro ANC Headphones): **$47,878.29** at risk (171 unit deficit, lead time 14 days).
  3. `SKU-011` (Mechanical Gaming Keyboard): **$46,237.28** at risk (272 unit deficit, lead time 28 days).
* **Finding 3: Lead Time Discrepancies Amplify Working Capital Requirements**
  SKUs sourced from overseas vendors (e.g. `SUP-104` with 28-day lead time) require **2.3x more safety stock** relative to weekly demand compared to domestic suppliers (e.g. `SUP-103` with 7-day lead time).
* **Finding 4: Predictive Accuracy Outperforms Static Moving Averages**
  The seasonal additive model (18.76% MAPE) captured Q4 holiday spikes and Q1 fitness surges, preventing the ~35% under-estimation error typical of naive moving averages.

---

## 5. Critical Priority Action Matrix (High-Risk SKUs)

The following 8 SKUs require **immediate purchase order creation**:

| SKU ID | Product Name | Category | Current Stock | Reorder Point (ROP) | Safety Stock | Deficit Units | Unit Price | Revenue at Risk ($) | Rec. Order Qty (EOQ Adj.) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SKU-004** | Dual-Motor Electric Standing Desk 60in | Office | 96 | 192 | 53 | 96 | $499.00 | **$47,904.00** | 111 |
| **SKU-001** | Pro Active Noise-Cancelling Headphones | Electronics | 163 | 334 | 93 | 171 | $279.99 | **$47,878.29** | 205 |
| **SKU-011** | Custom Mechanical Gaming Keyboard RGB | Electronics | 377 | 649 | 175 | 272 | $169.99 | **$46,237.28** | 353 |
| **SKU-002** | Smart Fitness GPS Watch Ultra | Electronics | 238 | 289 | 74 | 51 | $349.99 | **$17,849.49** | 163 |
| **SKU-017** | Inflatable Stand Up Touring Paddleboard | Outdoor | 49 | 96 | 32 | 47 | $369.00 | **$17,343.00** | 89 |
| **SKU-006** | Smart Auto-Empty Robotic Vacuum | Home | 172 | 209 | 59 | 37 | $399.99 | **$14,799.63** | 121 |
| **SKU-008** | Carbon Fiber Road Cycling Helmet | Outdoor | 94 | 161 | 48 | 67 | $189.50 | **$12,696.50** | 178 |
| **SKU-015** | XL 8-Quart Digital Dual-Zone Air Fryer | Home | 321 | 360 | 97 | 39 | $179.99 | **$7,019.61** | 241 |
| **TOTAL** | | | | | | **780** | | **$211,727.80** | **1,461** |

---

## 6. Strategic Recommendations

1. **Immediate Execution of Purchase Orders:**
   - Release purchase orders totaling **1,461 units** across the 8 deficit items. 
   - Ordering the recommended EOQ-adjusted quantities ensures that orders exceed the immediate deficit and minimize fixed ordering overhead.
2. **Expedite SKU-011 via Air Freight Split:**
   - Sourced from `SUP-104` with a 28-day maritime transit time.
   - Authorize air freight for 100 emergency units to cover stock during the 4-week transit period, shipping the remaining 253 units via ocean freight.
3. **Supplier Lead Time SLA Renegotiation:**
   - Negotiate a 5-day lead time reduction with `SUP-107` (Beacon Ergonomics, currently 18 days). A 5-day lead time reduction on `SKU-003` and `SKU-004` would reduce required safety stock by **16%**, unlocking ~$18,500 in working capital.
4. **Implement Dynamic ROP Thresholds:**
   - Rather than static annual reorder points, update ROP quarterly based on the 13-week forward forecast demand ($\bar{d}_{\text{forecast}}$) to adjust for seasonal swings.

---

## 7. Interactive Excel Dashboard (`dashboard/inventory_dashboard.xlsx`)

The generated multi-tab Excel workbook is pre-formatted with corporate styling:
- **Tab 1: Executive Summary:** High-level KPIs, at-risk revenue cards, and the prioritized emergency PO table.
- **Tab 2: Reorder Recommendations:** Complete Top 20 SKU table with dynamic conditional formatting (Red for High Risk, Yellow for Medium Risk, Green for Healthy).
- **Tab 3: Forecast vs Actuals:** Time-series tables containing actual demand, fitted values, and 13-week forward predictions with 80% confidence bounds.
- **Tab 4: ABC Revenue Analysis:** Full 50-item Pareto classification, cumulative revenue percentages, and category assignments.

---

## 8. Reproducibility & Execution Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Virtual environment recommended

### Installation & Run
```bash
# 1. Clone repository and navigate to directory
cd supply-chain-inventory-optimization

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run complete end-to-end pipeline
python run_pipeline.py
```

### Notebook Execution
Open Jupyter Notebook or JupyterLab to inspect the interactive analysis:
```bash
jupyter notebook notebooks/01_eda.ipynb
jupyter notebook notebooks/02_forecasting.ipynb
jupyter notebook notebooks/03_inventory_optimization.ipynb
```

---

## 9. Limitations & Next Steps

1. **Vendor Minimum Order Quantities (MOQs):** Real-world suppliers often enforce batch MOQs that exceed theoretical EOQ. Incorporating integer programming constraints is recommended.
2. **Lead Time Volatility ($SS_{\text{dual}}$):** Future iterations can apply dual-stochastic safety stock models:
   $$SS = Z \times \sqrt{L \cdot \sigma_D^2 + \bar{D}^2 \cdot \sigma_L^2}$$
   accounting for supplier shipment delays alongside demand variance.
3. **Price Elasticity & Promotions:** Integrating promotional calendars and promotional uplift multipliers directly into the time-series regression will further sharpen holiday peak predictions.
