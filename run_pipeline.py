#!/usr/bin/env python3
"""
run_pipeline.py
Master end-to-end execution pipeline for Supply Chain Demand Forecasting
& Inventory Optimization.

Orchestrates:
1. Data Synthesis & Anomaly Injection (scripts/generate_data.py)
2. Database Schema, Cleaning & Analytical Views (scripts/run_sql_pipeline.py)
3. Forecasting, Safety Stock, EOQ & Excel Dashboard (scripts/run_optimization_pipeline.py)
4. Verification & Summary Output
"""

import os
import sys
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

def run_step(step_num, title, script_name):
    print(f"\n[{step_num}/3] {title}")
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    start = time.time()
    result = subprocess.run([sys.executable, script_path], cwd=BASE_DIR)
    if result.returncode != 0:
        print(f"Error executing {script_name}! Exit code: {result.returncode}")
        sys.exit(result.returncode)
    print(f"Completed in {time.time() - start:.2f}s")

def main():
    print("=" * 75)
    print("SUPPLY CHAIN DEMAND FORECASTING & INVENTORY OPTIMIZATION PIPELINE")
    print("=" * 75)
    overall_start = time.time()
    
    # Step 1: Synthesize Raw Supply Chain Dataset
    run_step(1, "Synthesizing Transactional Dataset & Suppliers", "generate_data.py")
    
    # Step 2: Run SQL Schema, Sanitization & Aggregations
    run_step(2, "Executing SQL Ingestion, Cleaning & ABC Views", "run_sql_pipeline.py")
    
    # Step 3: Run Forecasting, Inventory Math & Dashboard Generation
    run_step(3, "Executing Forecasting, Safety Stock, ROP & Dashboard", "run_optimization_pipeline.py")
    
    total_time = time.time() - overall_start
    print("\n" + "=" * 75)
    print(f"PIPELINE EXECUTED SUCCESSFULLY IN {total_time:.2f} SECONDS")
    print("=" * 75)
    print("Deliverables available at:")
    print(f" - Clean SQL Database:  {os.path.join(BASE_DIR, 'data', 'supply_chain.db')}")
    print(f" - Processed Datasets:   {os.path.join(BASE_DIR, 'data', 'processed')}")
    print(f" - Forecast Results:    {os.path.join(BASE_DIR, 'outputs', 'forecast_results.csv')}")
    print(f" - Reorder Recs:        {os.path.join(BASE_DIR, 'outputs', 'reorder_recommendations.csv')}")
    print(f" - Excel Dashboard:     {os.path.join(BASE_DIR, 'dashboard', 'inventory_dashboard.xlsx')}")
    print(f" - Jupyter Notebooks:   {os.path.join(BASE_DIR, 'notebooks')}")
    print("=" * 75)

if __name__ == "__main__":
    main()
