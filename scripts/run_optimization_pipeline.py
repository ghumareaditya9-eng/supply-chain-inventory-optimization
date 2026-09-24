#!/usr/bin/env python3
"""
run_optimization_pipeline.py
Executes demand forecasting, mathematical inventory optimization, risk analysis,
and generates the Excel dashboard and CSV deliverables.

Steps:
1. Load cleaned datasets & identify Top 20 Revenue SKUs (ABC Class A).
2. For each top SKU:
   - Fit time-series forecasting model (trend + seasonality).
   - Evaluate against held-out 12-week test set (RMSE, MAE, MAPE).
   - Generate 13-week (1 quarter ahead, Q1-2025) demand forecasts.
3. Compute mathematical inventory models:
   - Safety Stock (Z = 1.65 for 95% service level)
   - Reorder Point (ROP = d_forecast * L + SS)
   - Economic Order Quantity (EOQ = sqrt(2 * D * S / H))
4. Evaluate stockout risks & quantify revenue at risk.
5. Export outputs/forecast_results.csv and outputs/reorder_recommendations.csv.
6. Build professional Excel workbook: dashboard/inventory_dashboard.xlsx.
"""

import os
import math
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(DASHBOARD_DIR, exist_ok=True)

def fit_forecast_model(train_series, forecast_periods=13):
    """
    Fits an additive trend and annual sinusoidal seasonality model.
    y(t) = alpha + beta * t + A * sin(2*pi*t/52) + B * cos(2*pi*t/52)
    This provides stable, highly interpretable decomposition with robust out-of-sample metrics.
    """
    n = len(train_series)
    t = np.arange(n)
    
    # Feature matrix: intercept, linear trend, 52-week annual harmonics
    X = np.column_stack([
        np.ones(n),
        t,
        np.sin(2 * np.pi * t / 52.0),
        np.cos(2 * np.pi * t / 52.0),
        np.sin(4 * np.pi * t / 52.0),
        np.cos(4 * np.pi * t / 52.0)
    ])
    
    y = np.array(train_series)
    
    # Solve ordinary least squares with light ridge regularization for numerical stability
    XtX = X.T @ X + 1e-4 * np.eye(X.shape[1])
    Xty = X.T @ y
    beta = np.linalg.solve(XtX, Xty)
    
    fitted_train = X @ beta
    residuals = y - fitted_train
    res_std = np.std(residuals)
    
    # Out of sample future prediction
    t_future = np.arange(n, n + forecast_periods)
    X_future = np.column_stack([
        np.ones(forecast_periods),
        t_future,
        np.sin(2 * np.pi * t_future / 52.0),
        np.cos(2 * np.pi * t_future / 52.0),
        np.sin(4 * np.pi * t_future / 52.0),
        np.cos(4 * np.pi * t_future / 52.0)
    ])
    
    forecast_vals = X_future @ beta
    # Constrain forecasts to non-negative
    forecast_vals = np.maximum(0, forecast_vals)
    
    return fitted_train, forecast_vals, res_std

def run():
    print("=" * 70)
    print("DEMAND FORECASTING & INVENTORY OPTIMIZATION ENGINE")
    print("=" * 70)
    
    # Load processed data
    weekly_df = pd.read_csv(os.path.join(PROCESSED_DIR, "weekly_demand.csv"))
    weekly_df["week_start"] = pd.to_datetime(weekly_df["week_start"])
    weekly_df = weekly_df.sort_values(["sku_id", "week_start"]).reset_index(drop=True)
    
    abc_df = pd.read_csv(os.path.join(PROCESSED_DIR, "sku_abc_classification.csv"))
    inv_df = pd.read_csv(os.path.join(BASE_DIR, "data", "raw", "inventory_master.csv"))
    supp_df = pd.read_csv(os.path.join(PROCESSED_DIR, "supplier_performance.csv"))
    
    # Identify Top 20 SKUs by total revenue
    top_20_skus = abc_df.head(20).copy()
    print(f"Loaded {len(top_20_skus)} Top SKUs by revenue for optimization.")
    
    # Holdout parameters
    test_weeks = 12
    forecast_weeks = 13 # 1 quarter ahead (Q1 2025)
    service_level_z = 1.65 # 95% cycle service level
    
    all_forecast_records = []
    reorder_records = []
    
    for _, sku_info in top_20_skus.iterrows():
        sku_id = sku_info["sku_id"]
        prod_name = sku_info["product_name"]
        cat = sku_info["category"]
        price = sku_info["unit_price"]
        cost = sku_info["unit_cost"]
        supp_id = sku_info["supplier_id"]
        
        sku_weeks = weekly_df[weekly_df["sku_id"] == sku_id].copy().sort_values("week_start").reset_index(drop=True)
        total_history_weeks = len(sku_weeks)
        
        train_df = sku_weeks.iloc[:-test_weeks]
        test_df = sku_weeks.iloc[-test_weeks:]
        
        # 1. Fit model on Train set and evaluate on Test set
        fitted_train, test_pred, train_res_std = fit_forecast_model(train_df["units_sold"].values, forecast_periods=test_weeks)
        
        test_actual = test_df["units_sold"].values
        mae = np.mean(np.abs(test_actual - test_pred))
        rmse = math.sqrt(np.mean((test_actual - test_pred)**2))
        mape = np.mean(np.abs((test_actual - test_pred) / np.maximum(1, test_actual))) * 100.0
        
        # 2. Refit on entire 104 weeks history to forecast next 13 weeks (Q1 2025)
        fitted_full, q1_forecast, full_res_std = fit_forecast_model(sku_weeks["units_sold"].values, forecast_periods=forecast_weeks)
        
        last_date = sku_weeks["week_start"].max()
        future_dates = [last_date + pd.Timedelta(weeks=i+1) for i in range(forecast_weeks)]
        
        # Record historical rows for output
        for i, row in sku_weeks.iterrows():
            split_label = "Train" if i < (total_history_weeks - test_weeks) else "Test"
            model_val = fitted_full[i]
            all_forecast_records.append({
                "sku_id": sku_id,
                "product_name": prod_name,
                "category": cat,
                "week_start": row["week_start"].strftime("%Y-%m-%d"),
                "actual_demand": round(float(row["units_sold"]), 1),
                "model_forecast": round(float(model_val), 1),
                "lower_bound_80pct": round(max(0, float(model_val - 1.28 * full_res_std)), 1),
                "upper_bound_80pct": round(float(model_val + 1.28 * full_res_std), 1),
                "split": split_label
            })
            
        # Record future forecast rows
        for i in range(forecast_weeks):
            f_val = q1_forecast[i]
            all_forecast_records.append({
                "sku_id": sku_id,
                "product_name": prod_name,
                "category": cat,
                "week_start": future_dates[i].strftime("%Y-%m-%d"),
                "actual_demand": None,
                "model_forecast": round(float(f_val), 1),
                "lower_bound_80pct": round(max(0, float(f_val - 1.28 * full_res_std)), 1),
                "upper_bound_80pct": round(float(f_val + 1.28 * full_res_std), 1),
                "split": "Forecast"
            })
            
        # 3. Inventory Optimization Math
        # Supplier lead time metrics
        supp_perf = supp_df[supp_df["supplier_id"] == supp_id].iloc[0]
        lead_time_days = supp_perf["avg_lead_time_days"]
        lead_time_weeks = lead_time_days / 7.0
        
        # Demand statistics
        avg_forecast_weekly = np.mean(q1_forecast)
        quarterly_forecast_demand = np.sum(q1_forecast)
        annual_forecast_demand = avg_forecast_weekly * 52.0
        sigma_demand_weekly = np.std(sku_weeks["units_sold"].values)
        
        # On-hand inventory from master
        inv_item = inv_df[inv_df["sku_id"] == sku_id].iloc[0]
        current_stock = int(inv_item["current_stock"])
        order_cost = float(inv_item["order_cost"])
        holding_rate = float(inv_item["holding_cost_annual_rate"])
        annual_unit_holding_cost = round(cost * holding_rate, 2)
        
        # Safety Stock formula: SS = Z * sigma_demand * sqrt(lead_time_weeks)
        safety_stock = math.ceil(service_level_z * sigma_demand_weekly * math.sqrt(lead_time_weeks))
        
        # Reorder Point (ROP) = (avg_demand_weekly * lead_time_weeks) + safety_stock
        lead_time_demand = avg_forecast_weekly * lead_time_weeks
        reorder_point = math.ceil(lead_time_demand + safety_stock)
        
        # Economic Order Quantity: EOQ = sqrt(2 * D_annual * S / H)
        eoq = math.ceil(math.sqrt((2.0 * annual_forecast_demand * order_cost) / annual_unit_holding_cost))
        
        # Stockout Risk Evaluation
        if current_stock < reorder_point:
            risk_status = "HIGH RISK"
            deficit_units = reorder_point - current_stock
            rec_order_qty = max(eoq, deficit_units)
        elif current_stock < (reorder_point + 0.5 * safety_stock):
            risk_status = "MEDIUM RISK"
            deficit_units = 0
            rec_order_qty = eoq
        else:
            risk_status = "HEALTHY"
            deficit_units = 0
            rec_order_qty = 0
            
        revenue_at_risk = round(deficit_units * price, 2)
        
        reorder_records.append({
            "sku_id": sku_id,
            "product_name": prod_name,
            "category": cat,
            "abc_class": sku_info["abc_category"],
            "unit_price": price,
            "unit_cost": cost,
            "supplier_id": supp_id,
            "lead_time_days": round(lead_time_days, 1),
            "lead_time_weeks": round(lead_time_weeks, 2),
            "avg_forecast_weekly": round(avg_forecast_weekly, 1),
            "quarterly_forecast_demand": round(quarterly_forecast_demand, 0),
            "annual_forecast_demand": round(annual_forecast_demand, 0),
            "demand_stddev_weekly": round(sigma_demand_weekly, 2),
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "current_stock": current_stock,
            "eoq": eoq,
            "risk_status": risk_status,
            "units_at_risk": deficit_units,
            "revenue_at_risk": revenue_at_risk,
            "recommended_order_qty": rec_order_qty,
            "test_rmse": round(rmse, 2),
            "test_mae": round(mae, 2),
            "test_mape_pct": round(mape, 2)
        })

    # Save outputs
    forecast_df = pd.DataFrame(all_forecast_records)
    reorder_df = pd.DataFrame(reorder_records)
    
    forecast_csv_path = os.path.join(OUTPUTS_DIR, "forecast_results.csv")
    reorder_csv_path = os.path.join(OUTPUTS_DIR, "reorder_recommendations.csv")
    
    forecast_df.to_csv(forecast_csv_path, index=False)
    reorder_df.to_csv(reorder_csv_path, index=False)
    print(f"\n[OK] Saved forecast results to: {forecast_csv_path}")
    print(f"[OK] Saved reorder recommendations to: {reorder_csv_path}")
    
    # Print Executive Summary of Results
    total_rev_at_risk = reorder_df["revenue_at_risk"].sum()
    high_risk_skus = reorder_df[reorder_df["risk_status"] == "HIGH RISK"]
    avg_mape = reorder_df["test_mape_pct"].mean()
    
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY OF FINDINGS")
    print("=" * 70)
    print(f"Top 20 SKUs Forecast Model Avg MAPE: {avg_mape:.2f}%")
    print(f"SKUs at HIGH STOCKOUT RISK: {len(high_risk_skus)} of 20")
    print(f"Total Immediate Revenue at Risk: ${total_rev_at_risk:,.2f}")
    print("\nCritical SKUs requiring immediate purchase order trigger:")
    for _, r in high_risk_skus.iterrows():
        print(f" - {r['sku_id']} ({r['product_name']}): Current Stock {r['current_stock']} < ROP {r['reorder_point']} | Deficit: {r['units_at_risk']} units | At-Risk Rev: ${r['revenue_at_risk']:,.2f} | Rec Order: {r['recommended_order_qty']} units")

    # 4. Generate Professional Excel Dashboard
    build_excel_dashboard(reorder_df, forecast_df, abc_df)

def build_excel_dashboard(reorder_df, forecast_df, abc_df):
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)
    
    # Styles
    navy_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    dark_gray_fill = PatternFill(start_color="2F3542", end_color="2F3542", fill_type="solid")
    light_blue_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    light_gray_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    red_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    yellow_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    green_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    
    font_title = Font(name="Calibri", size=16, bold=True, color="1F4E79")
    font_section = Font(name="Calibri", size=13, bold=True, color="2F3542")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_regular = Font(name="Calibri", size=11)
    
    font_high_risk = Font(name="Calibri", size=11, bold=True, color="C00000")
    font_med_risk = Font(name="Calibri", size=11, bold=True, color="B25900")
    font_healthy = Font(name="Calibri", size=11, bold=True, color="375623")
    
    thin_border = Border(
        left=Side(style='thin', color="D3D3D3"),
        right=Side(style='thin', color="D3D3D3"),
        top=Side(style='thin', color="D3D3D3"),
        bottom=Side(style='thin', color="D3D3D3")
    )
    
    # -------------------------------------------------------------
    # TAB 1: EXECUTIVE KPI SUMMARY
    # -------------------------------------------------------------
    ws1 = wb.create_sheet(title="Executive Summary")
    ws1.views.sheetView[0].showGridLines = True
    
    ws1["A1"] = "SUPPLY CHAIN DEMAND FORECASTING & INVENTORY OPTIMIZATION"
    ws1["A1"].font = font_title
    ws1["A2"] = "Executive Decision Dashboard — Top 20 Revenue SKUs (Quarterly Optimization)"
    ws1["A2"].font = Font(name="Calibri", size=11, italic=True, color="595959")
    
    ws1["A4"] = "KEY PERFORMANCE INDICATORS (KPIs)"
    ws1["A4"].font = font_section
    
    kpis = [
        ("Top 20 Revenue Share", f"{abc_df.head(20)['cumulative_revenue_pct'].iloc[-1]:.1f}% of Catalog"),
        ("Model Accuracy (Avg MAPE)", f"{reorder_df['test_mape_pct'].mean():.2f}%"),
        ("Total Active SKUs Evaluated", "20 SKUs"),
        ("High Stockout Risk SKUs", f"{len(reorder_df[reorder_df['risk_status'] == 'HIGH RISK'])} SKUs"),
        ("Medium Stockout Risk SKUs", f"{len(reorder_df[reorder_df['risk_status'] == 'MEDIUM RISK'])} SKUs"),
        ("Total Immediate Revenue at Risk", f"${reorder_df['revenue_at_risk'].sum():,.2f}"),
        ("Recommended Immediate Order Units", f"{reorder_df[reorder_df['risk_status'] == 'HIGH RISK']['recommended_order_qty'].sum():,} units")
    ]
    
    for idx, (label, val) in enumerate(kpis):
        row = 5 + idx
        ws1[f"A{row}"] = label
        ws1[f"A{row}"].font = font_bold
        ws1[f"A{row}"].fill = light_gray_fill
        ws1[f"A{row}"].border = thin_border
        
        ws1[f"B{row}"] = val
        ws1[f"B{row}"].font = font_bold if "Risk" in label or "Accuracy" in label else font_regular
        ws1[f"B{row}"].alignment = Alignment(horizontal="right")
        ws1[f"B{row}"].border = thin_border
        if "High" in label or "Revenue at Risk" in label:
            ws1[f"B{row}"].fill = red_fill
            ws1[f"B{row}"].font = font_high_risk
            
    # Priority Action Table
    ws1["A14"] = "CRITICAL ACTION REQUIRED: IMMEDIATE PURCHASE ORDERS"
    ws1["A14"].font = font_section
    
    headers1 = ["SKU ID", "Product Name", "Category", "Current Stock", "Reorder Point (ROP)", "Safety Stock", "Deficit Units", "Revenue at Risk ($)", "Rec. Order Qty (EOQ Adjusted)"]
    for c_idx, h in enumerate(headers1, 1):
        cell = ws1.cell(row=15, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        
    crit_df = reorder_df[reorder_df["risk_status"] == "HIGH RISK"].sort_values("revenue_at_risk", ascending=False)
    for r_idx, (_, r) in enumerate(crit_df.iterrows(), 16):
        vals = [
            r["sku_id"], r["product_name"], r["category"],
            r["current_stock"], r["reorder_point"], r["safety_stock"],
            r["units_at_risk"], r["revenue_at_risk"], r["recommended_order_qty"]
        ]
        for c_idx, val in enumerate(vals, 1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx in [4, 5, 6, 7, 9]:
                cell.alignment = Alignment(horizontal="right")
            if c_idx == 8:
                cell.number_format = '$#,##0.00'
                cell.font = font_high_risk
                cell.fill = red_fill
            elif c_idx == 4:
                cell.font = font_bold
                cell.fill = red_fill

    # -------------------------------------------------------------
    # TAB 2: INVENTORY OPTIMIZATION & REORDER RECOMMENDATIONS
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Reorder Recommendations")
    ws2.views.sheetView[0].showGridLines = True
    
    ws2["A1"] = "INVENTORY OPTIMIZATION MASTER TABLE (TOP 20 SKUs)"
    ws2["A1"].font = font_title
    
    headers2 = [
        "SKU ID", "Product Name", "Category", "ABC Class", "Unit Price", "Unit Cost",
        "Supplier", "Lead Time (Days)", "Weekly Forecast", "Q1 Forecast Demand",
        "Demand StdDev", "Safety Stock (SS)", "Reorder Point (ROP)", "Current Stock",
        "EOQ", "Risk Status", "Units at Risk", "Revenue at Risk ($)", "Rec. Order Qty"
    ]
    
    for c_idx, h in enumerate(headers2, 1):
        cell = ws2.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = dark_gray_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        
    for r_idx, (_, r) in enumerate(reorder_df.iterrows(), 4):
        row_vals = [
            r["sku_id"], r["product_name"], r["category"], r["abc_class"],
            r["unit_price"], r["unit_cost"], r["supplier_id"], r["lead_time_days"],
            r["avg_forecast_weekly"], r["quarterly_forecast_demand"], r["demand_stddev_weekly"],
            r["safety_stock"], r["reorder_point"], r["current_stock"], r["eoq"],
            r["risk_status"], r["units_at_risk"], r["revenue_at_risk"], r["recommended_order_qty"]
        ]
        
        status = r["risk_status"]
        for c_idx, val in enumerate(row_vals, 1):
            cell = ws2.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            
            # Alignments & Formats
            if c_idx in [5, 6]:
                cell.number_format = '$#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif c_idx == 18:
                cell.number_format = '$#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif c_idx in [8, 9, 10, 11, 12, 13, 14, 15, 17, 19]:
                cell.alignment = Alignment(horizontal="right")
            elif c_idx in [1, 4, 7, 16]:
                cell.alignment = Alignment(horizontal="center")
                
            # Conditional formatting fill on Risk Status
            if c_idx == 16:
                if status == "HIGH RISK":
                    cell.fill = red_fill
                    cell.font = font_high_risk
                elif status == "MEDIUM RISK":
                    cell.fill = yellow_fill
                    cell.font = font_med_risk
                else:
                    cell.fill = green_fill
                    cell.font = font_healthy

    # -------------------------------------------------------------
    # TAB 3: FORECAST VS ACTUALS
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Forecast vs Actuals")
    ws3.views.sheetView[0].showGridLines = True
    
    ws3["A1"] = "DEMAND FORECASTING TIME-SERIES (ACTUALS, FITTED & Q1-2025 PREDICTIONS)"
    ws3["A1"].font = font_title
    
    headers3 = ["SKU ID", "Product Name", "Category", "Week Start", "Actual Units", "Model Forecast", "Lower 80% CI", "Upper 80% CI", "Data Split"]
    for c_idx, h in enumerate(headers3, 1):
        cell = ws3.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        
    for r_idx, (_, r) in enumerate(forecast_df.iterrows(), 4):
        row_vals = [
            r["sku_id"], r["product_name"], r["category"], r["week_start"],
            r["actual_demand"], r["model_forecast"], r["lower_bound_80pct"], r["upper_bound_80pct"], r["split"]
        ]
        for c_idx, val in enumerate(row_vals, 1):
            cell = ws3.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx in [5, 6, 7, 8]:
                cell.alignment = Alignment(horizontal="right")
                if val is not None:
                    cell.number_format = '#,##0.0'
            elif c_idx in [1, 4, 9]:
                cell.alignment = Alignment(horizontal="center")

    # -------------------------------------------------------------
    # TAB 4: ABC ANALYSIS
    # -------------------------------------------------------------
    ws4 = wb.create_sheet(title="ABC Revenue Analysis")
    ws4.views.sheetView[0].showGridLines = True
    
    ws4["A1"] = "PARETO ABC REVENUE SEGMENTATION (FULL 50 SKU CATALOG)"
    ws4["A1"].font = font_title
    
    headers4 = ["SKU ID", "Product Name", "Category", "Unit Price", "Total Units Sold", "Total Revenue ($)", "Cumulative Revenue %", "ABC Category"]
    for c_idx, h in enumerate(headers4, 1):
        cell = ws4.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = dark_gray_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        
    for r_idx, (_, r) in enumerate(abc_df.iterrows(), 4):
        row_vals = [
            r["sku_id"], r["product_name"], r["category"], r["unit_price"],
            r["total_units"], r["total_revenue"], r["cumulative_revenue_pct"], r["abc_category"]
        ]
        for c_idx, val in enumerate(row_vals, 1):
            cell = ws4.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx in [4, 6]:
                cell.number_format = '$#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif c_idx == 5:
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal="right")
            elif c_idx == 7:
                cell.number_format = '0.00"%"'
                cell.alignment = Alignment(horizontal="right")
            elif c_idx in [1, 8]:
                cell.alignment = Alignment(horizontal="center")
                if c_idx == 8:
                    if val == "A":
                        cell.fill = green_fill
                        cell.font = font_bold
                    elif val == "B":
                        cell.fill = yellow_fill
                    else:
                        cell.fill = light_gray_fill

    # Auto-adjust column widths across all sheets
    for ws in [ws1, ws2, ws3, ws4]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row in [1, 2]: # Skip main titles
                    continue
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    dashboard_path = os.path.join(DASHBOARD_DIR, "inventory_dashboard.xlsx")
    wb.save(dashboard_path)
    print(f"\n[OK] Successfully generated Excel Dashboard: {dashboard_path}")

if __name__ == "__main__":
    run()
