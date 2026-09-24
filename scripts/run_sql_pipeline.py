#!/usr/bin/env python3
"""
run_sql_pipeline.py
Executes the full SQL lifecycle:
1. Initializes SQLite database (data/supply_chain.db)
2. Loads schema from sql/01_schema.sql
3. Loads raw CSV data into staging tables
4. Executes data sanitization and deduplication via sql/02_cleaning.sql
5. Computes analytics views via sql/03_aggregations.sql
6. Exports clean data and analytical views to data/processed/ for modeling & dashboards
"""

import os
import sqlite3
import csv
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "supply_chain.db")
SQL_DIR = os.path.join(BASE_DIR, "sql")
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

def run():
    print("=" * 70)
    print("STARTING SQL DATA PIPELINE EXECUTION")
    print("=" * 70)
    start_time = time.time()
    
    # Remove existing db if present to ensure fresh rebuild
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
            
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable performance settings for batch ingestion
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")
    
    # 1. Execute Schema Creation
    print("\n[Step 1/5] Applying 01_schema.sql...")
    with open(os.path.join(SQL_DIR, "01_schema.sql"), "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    print(" -> Tables (raw_orders, cleaned_orders, inventory_master) successfully initialized.")
    
    # 2. Ingest Raw Orders
    raw_orders_csv = os.path.join(RAW_DATA_DIR, "supply_chain_raw.csv")
    print(f"\n[Step 2/5] Ingesting raw orders from {os.path.basename(raw_orders_csv)}...")
    with open(raw_orders_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        insert_raw_query = """
        INSERT INTO raw_orders (
            order_id, order_date, customer_id, sku_id, product_name, category,
            unit_price, unit_cost, quantity, supplier_id, supplier_lead_time_days,
            order_cost, holding_cost_annual_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_raw_query, reader)
    
    # Ingest Inventory Master
    inv_master_csv = os.path.join(RAW_DATA_DIR, "inventory_master.csv")
    print(f" -> Ingesting inventory master from {os.path.basename(inv_master_csv)}...")
    with open(inv_master_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        insert_inv_query = """
        INSERT INTO inventory_master (
            sku_id, product_name, category, current_stock, unit_price,
            unit_cost, supplier_id, holding_cost_annual_rate, order_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_inv_query, reader)
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM raw_orders;")
    raw_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM inventory_master;")
    inv_count = cursor.fetchone()[0]
    print(f" -> Raw orders ingested: {raw_count:,} records.")
    print(f" -> Inventory master records: {inv_count} SKUs.")
    
    # 3. Execute Cleaning and Deduplication
    print("\n[Step 3/5] Applying 02_cleaning.sql...")
    with open(os.path.join(SQL_DIR, "02_cleaning.sql"), "r", encoding="utf-8") as f:
        cleaning_sql = f.read()
    cursor.executescript(cleaning_sql)
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM cleaned_orders;")
    clean_count = cursor.fetchone()[0]
    filtered_count = raw_count - clean_count
    print(f" -> Cleaned records retained: {clean_count:,}")
    print(f" -> Corrupt / duplicate records eliminated: {filtered_count:,} ({(filtered_count / raw_count)*100:.2f}%)")
    
    # 4. Execute Aggregations & Analytical Views
    print("\n[Step 4/5] Applying 03_aggregations.sql...")
    with open(os.path.join(SQL_DIR, "03_aggregations.sql"), "r", encoding="utf-8") as f:
        agg_sql = f.read()
    cursor.executescript(agg_sql)
    conn.commit()
    print(" -> Aggregation views created successfully.")
    
    # 5. Export processed views to CSV
    print("\n[Step 5/5] Exporting clean data and analytical views to data/processed/...")
    
    exports = [
        ("SELECT * FROM cleaned_orders", "cleaned_orders.csv"),
        ("SELECT * FROM v_weekly_demand_by_sku", "weekly_demand.csv"),
        ("SELECT * FROM v_monthly_demand_by_sku", "monthly_demand.csv"),
        ("SELECT * FROM v_supplier_performance", "supplier_performance.csv"),
        ("SELECT * FROM v_sku_demand_variability", "sku_demand_variability.csv"),
        ("SELECT * FROM v_sku_abc_classification", "sku_abc_classification.csv"),
    ]
    
    for query, filename in exports:
        out_path = os.path.join(PROCESSED_DATA_DIR, filename)
        cursor.execute(query)
        headers = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f" -> Exported {filename} ({len(rows):,} rows)")
        
    conn.close()
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"SQL PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f}s")
    print("=" * 70)

if __name__ == "__main__":
    run()
