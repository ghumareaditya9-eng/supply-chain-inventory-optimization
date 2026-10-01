#!/usr/bin/env python3
"""
generate_interactive_bi_dashboard.py
Generates a standalone, fully interactive Executive BI Web Dashboard (interactive_dashboard.html)
mirroring a production Power BI report with Chart.js charts, KPI cards, category slicers,
and a priority purchase order table.
"""

import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

def build():
    reorder_df = pd.read_csv(os.path.join(OUTPUTS_DIR, "reorder_recommendations.csv"))
    forecast_df = pd.read_csv(os.path.join(OUTPUTS_DIR, "forecast_results.csv"))
    abc_df = pd.read_csv(os.path.join(PROCESSED_DIR, "sku_abc_classification.csv"))
    
    total_rev_at_risk = reorder_df["revenue_at_risk"].sum()
    high_risk_count = len(reorder_df[reorder_df["risk_status"] == "HIGH RISK"])
    total_skus = len(reorder_df)
    avg_mape = reorder_df["test_mape_pct"].mean()
    total_rec_units = reorder_df[reorder_df["risk_status"] == "HIGH RISK"]["recommended_order_qty"].sum()
    
    # Category Risk Breakdown
    cat_risk = reorder_df.groupby("category")["revenue_at_risk"].sum().reset_index()
    cat_risk = cat_risk.sort_values("revenue_at_risk", ascending=False)
    
    # Forecast sample for SKU-001 (Noise-Cancelling Headphones)
    sku_001 = forecast_df[forecast_df["sku_id"] == "SKU-001"].copy()
    dates = sku_001["week_start"].tolist()
    actuals = [None if pd.isna(x) else float(x) for x in sku_001["actual_demand"]]
    forecasts = [float(x) for x in sku_001["model_forecast"]]
    lower_ci = [float(x) for x in sku_001["lower_bound_80pct"]]
    upper_ci = [float(x) for x in sku_001["upper_bound_80pct"]]
    
    # Pareto Data (Top 25 SKUs)
    pareto_top = abc_df.head(25)
    pareto_skus = pareto_top["product_name"].tolist()
    pareto_rev = (pareto_top["total_revenue"] / 1000.0).round(1).tolist()
    pareto_cum = pareto_top["cumulative_revenue_pct"].tolist()
    
    # Convert reorder_df to JSON records
    table_records = reorder_df.to_dict(orient="records")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Supply Chain Executive BI Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --primary: #1F4E79;
            --primary-dark: #14324f;
            --danger: #E74C3C;
            --warning: #F39C12;
            --success: #2ECC71;
            --bg: #F4F6F9;
            --card-bg: #FFFFFF;
            --text-dark: #2C3E50;
            --text-muted: #7F8C8D;
            --border: #E2E8F0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-dark); padding: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }}
        .header-title h1 {{ font-size: 24px; color: var(--primary); font-weight: 700; }}
        .header-title p {{ font-size: 14px; color: var(--text-muted); margin-top: 4px; }}
        .badge-live {{ background-color: #E8F8F5; color: var(--success); padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 13px; border: 1px solid #A3E4D7; }}
        
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-bottom: 24px; }}
        .kpi-card {{ background: var(--card-bg); border-radius: 12px; padding: 20px; border: 1px solid var(--border); box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
        .kpi-label {{ font-size: 13px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }}
        .kpi-val {{ font-size: 28px; font-weight: 700; margin-top: 8px; color: var(--primary-dark); }}
        .kpi-sub {{ font-size: 12px; margin-top: 6px; }}
        .kpi-danger .kpi-val {{ color: var(--danger); }}
        .kpi-success .kpi-val {{ color: var(--success); }}
        
        .charts-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px; }}
        .charts-row-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
        .card {{ background: var(--card-bg); border-radius: 12px; padding: 22px; border: 1px solid var(--border); box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
        .card-title {{ font-size: 16px; font-weight: 700; color: var(--primary-dark); }}
        .card-subtitle {{ font-size: 12px; color: var(--text-muted); }}
        
        .table-container {{ overflow-x: auto; margin-top: 12px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
        th {{ background: #F8FAFC; color: var(--text-muted); font-weight: 600; padding: 12px 14px; border-bottom: 1px solid var(--border); }}
        td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); }}
        tr:hover {{ background-color: #F8FAFC; }}
        
        .badge {{ padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; display: inline-block; }}
        .badge-danger {{ background: #FDEDEC; color: var(--danger); border: 1px solid #FADBD8; }}
        .badge-warning {{ background: #FEF9E7; color: #D68910; border: 1px solid #FCF3CF; }}
        .badge-success {{ background: #EAFAF1; color: var(--success); border: 1px solid #D4EFDF; }}
        
        .filter-bar {{ display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }}
        .filter-select, .search-box {{ padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; outline: none; }}
        .search-box {{ flex-grow: 1; max-width: 320px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">
            <h1>Supply Chain Demand Forecasting & Inventory Optimization</h1>
            <p>Executive Decision Dashboard • Top 20 Revenue SKUs (Quarterly Review: Q1-2025)</p>
        </div>
        <div>
            <span class="badge-live">● System Live • Power BI Architecture</span>
        </div>
    </div>

    <!-- Top KPI Cards -->
    <div class="kpi-grid">
        <div class="kpi-card kpi-danger">
            <div class="kpi-label">Total Revenue at Risk</div>
            <div class="kpi-val">${total_rev_at_risk:,.2f}</div>
            <div class="kpi-sub" style="color: var(--danger);">Immediate stockout deficit across 8 critical SKUs</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Stockout Risk Rate</div>
            <div class="kpi-val">{high_risk_count} / {total_skus} SKUs</div>
            <div class="kpi-sub" style="color: var(--text-muted);">40% of Class A items below Reorder Point</div>
        </div>
        <div class="kpi-card kpi-success">
            <div class="kpi-label">Forecast Model Accuracy</div>
            <div class="kpi-val">{avg_mape:.2f}% MAPE</div>
            <div class="kpi-sub" style="color: var(--success);">Validated on 12-week out-of-sample holdout</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Recommended Replenishment</div>
            <div class="kpi-val">{total_rec_units:,} Units</div>
            <div class="kpi-sub" style="color: var(--text-muted);">EOQ-adjusted purchase orders to eliminate deficit</div>
        </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="charts-grid">
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">Demand Forecasting Trajectory (SKU-001: Pro ANC Headphones)</div>
                    <div class="card-subtitle">104 Weeks Historical Actuals + 13 Weeks Q1-2025 Forecast with 80% Prediction Interval</div>
                </div>
            </div>
            <div style="height: 280px;">
                <canvas id="forecastChart"></canvas>
            </div>
        </div>
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">Revenue at Risk by Category</div>
                    <div class="card-subtitle">Financial exposure breakdown ($ USD)</div>
                </div>
            </div>
            <div style="height: 280px;">
                <canvas id="categoryRiskChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="charts-row-2">
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">Pareto ABC Cumulative Revenue Distribution</div>
                    <div class="card-subtitle">Top 25 Catalog SKUs Revenue vs 80% Pareto Threshold</div>
                </div>
            </div>
            <div style="height: 260px;">
                <canvas id="paretoChart"></canvas>
            </div>
        </div>
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">Stockout Risk Category Distribution</div>
                    <div class="card-subtitle">Percentage of Top 20 SKUs by Inventory Status</div>
                </div>
            </div>
            <div style="height: 260px;">
                <canvas id="riskDonutChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Master Action Table -->
    <div class="card">
        <div class="card-header">
            <div>
                <div class="card-title">Priority Replenishment & Decision Matrix</div>
                <div class="card-subtitle">Real-time status of Top 20 revenue drivers with recommended PO sizes</div>
            </div>
        </div>
        <div class="filter-bar">
            <input type="text" id="searchInput" class="search-box" placeholder="Search product or SKU..." onkeyup="filterTable()">
            <select id="statusFilter" class="filter-select" onchange="filterTable()">
                <option value="ALL">All Risk Statuses</option>
                <option value="HIGH RISK">High Risk Only</option>
                <option value="HEALTHY">Healthy Only</option>
            </select>
        </div>
        <div class="table-container">
            <table id="reorderTable">
                <thead>
                    <tr>
                        <th>SKU ID</th>
                        <th>Product Name</th>
                        <th>Category</th>
                        <th>Lead Time</th>
                        <th>Weekly Demand</th>
                        <th>Safety Stock</th>
                        <th>Reorder Point</th>
                        <th>Current Stock</th>
                        <th>Status</th>
                        <th>At-Risk Revenue</th>
                        <th>Recommended Order</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for row in table_records:
        badge_class = "badge-danger" if row["risk_status"] == "HIGH RISK" else ("badge-warning" if row["risk_status"] == "MEDIUM RISK" else "badge-success")
        rev_color = "style='color: var(--danger); font-weight: 700;'" if row["risk_status"] == "HIGH RISK" else "style='color: var(--text-muted);'"
        html_content += f"""
                    <tr>
                        <td><strong>{row['sku_id']}</strong></td>
                        <td>{row['product_name']}</td>
                        <td>{row['category']}</td>
                        <td>{row['lead_time_days']} days</td>
                        <td>{row['avg_forecast_weekly']:.1f}</td>
                        <td>{row['safety_stock']}</td>
                        <td><strong>{row['reorder_point']}</strong></td>
                        <td>{row['current_stock']}</td>
                        <td><span class="badge {badge_class}">{row['risk_status']}</span></td>
                        <td {rev_color}>${row['revenue_at_risk']:,.2f}</td>
                        <td><strong>{row['recommended_order_qty']:,} units</strong></td>
                    </tr>"""
                    
    html_content += f"""
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // 1. Forecast Chart
        const dates = {json.dumps(dates)};
        const actuals = {json.dumps(actuals)};
        const forecasts = {json.dumps(forecasts)};
        const upperCI = {json.dumps(upper_ci)};
        const lowerCI = {json.dumps(lower_ci)};

        new Chart(document.getElementById('forecastChart'), {{
            type: 'line',
            data: {{
                labels: dates,
                datasets: [
                    {{
                        label: 'Actual Demand',
                        data: actuals,
                        borderColor: '#2C3E50',
                        backgroundColor: '#2C3E50',
                        borderWidth: 1.5,
                        pointRadius: 0
                    }},
                    {{
                        label: 'Model Forecast',
                        data: forecasts,
                        borderColor: '#1F4E79',
                        backgroundColor: '#1F4E79',
                        borderWidth: 2.2,
                        pointRadius: 0
                    }},
                    {{
                        label: 'Upper 80% CI',
                        data: upperCI,
                        borderColor: 'rgba(231, 76, 60, 0.4)',
                        borderDash: [4, 4],
                        pointRadius: 0,
                        fill: false
                    }},
                    {{
                        label: 'Lower 80% CI',
                        data: lowerCI,
                        borderColor: 'rgba(231, 76, 60, 0.4)',
                        borderDash: [4, 4],
                        pointRadius: 0,
                        fill: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ ticks: {{ maxTicksLimit: 12, font: {{ size: 10 }} }} }},
                    y: {{ title: {{ display: true, text: 'Units Sold' }} }}
                }}
            }}
        }});

        // 2. Category Risk Bar Chart
        new Chart(document.getElementById('categoryRiskChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(cat_risk['category'].tolist())},
                datasets: [{{
                    label: 'Revenue at Risk ($)',
                    data: {json.dumps(cat_risk['revenue_at_risk'].tolist())},
                    backgroundColor: '#E74C3C',
                    borderRadius: 4
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ x: {{ ticks: {{ callback: v => '$' + (v/1000) + 'k' }} }} }}
            }}
        }});

        // 3. Pareto Chart
        new Chart(document.getElementById('paretoChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(pareto_skus[:15])},
                datasets: [
                    {{
                        type: 'line',
                        label: 'Cumulative Revenue %',
                        data: {json.dumps(pareto_cum[:15])},
                        borderColor: '#E74C3C',
                        borderWidth: 2,
                        yAxisID: 'y1',
                        pointRadius: 3
                    }},
                    {{
                        type: 'bar',
                        label: 'Revenue ($k)',
                        data: {json.dumps(pareto_rev[:15])},
                        backgroundColor: '#1F4E79',
                        yAxisID: 'y',
                        borderRadius: 4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ ticks: {{ maxRotation: 45, minRotation: 45, font: {{ size: 9 }} }} }},
                    y: {{ title: {{ display: true, text: 'Revenue ($k)' }} }},
                    y1: {{ position: 'right', min: 0, max: 100, ticks: {{ callback: v => v + '%' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});

        // 4. Donut Chart
        new Chart(document.getElementById('riskDonutChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['High Risk (Deficit)', 'Healthy Buffer'],
                datasets: [{{
                    data: [{high_risk_count}, {total_skus - high_risk_count}],
                    backgroundColor: ['#E74C3C', '#2ECC71'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom' }} }}
            }}
        }});

        // Table Filter Function
        function filterTable() {{
            const search = document.getElementById('searchInput').value.toUpperCase();
            const status = document.getElementById('statusFilter').value;
            const rows = document.getElementById('reorderTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            
            for (let row of rows) {{
                const text = row.innerText.toUpperCase();
                const rowStatus = row.cells[8].innerText.trim();
                const matchSearch = text.includes(search);
                const matchStatus = (status === 'ALL') || (rowStatus === status);
                row.style.display = (matchSearch && matchStatus) ? '' : 'none';
            }}
        }}
    </script>
</body>
</html>
"""
    
    html_path = os.path.join(DASHBOARD_DIR, "interactive_dashboard.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Generated Interactive BI Dashboard: {html_path}")

if __name__ == "__main__":
    build()
