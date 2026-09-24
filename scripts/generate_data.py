#!/usr/bin/env python3
"""
generate_data.py
Synthesizes a realistic, high-fidelity supply chain transaction dataset modeled on
the DataCo Smart Supply Chain & Store Item Demand datasets.

Includes realistic demand drivers:
- SKU baseline demand & price elasticities
- Trend + Weekly & Annual Seasonality (e.g., Q4 Holiday surges, Summer outdoor spikes)
- Supplier-specific lead times and variability
- Injected anomalies (duplicates, nulls, negative quantities) for SQL cleaning verification
- Optimized row volume (~26,000 transactions across 104 weeks for 50 SKUs) for high speed & memory efficiency
"""

import os
import random
import csv
from datetime import datetime, timedelta
import math

# Set random seed for complete reproducibility
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DATA_DIR, exist_ok=True)

SUPPLIERS = [
    {"supplier_id": "SUP-101", "name": "Pacific Tech Logistics", "lead_time_mean": 14, "lead_time_sd": 2.5, "order_cost": 85.0},
    {"supplier_id": "SUP-102", "name": "Apex Nordic Hardware", "lead_time_mean": 21, "lead_time_sd": 4.0, "order_cost": 110.0},
    {"supplier_id": "SUP-103", "name": "Midwest Express Components", "lead_time_mean": 7, "lead_time_sd": 1.2, "order_cost": 50.0},
    {"supplier_id": "SUP-104", "name": "Shenzhen Global Direct", "lead_time_mean": 28, "lead_time_sd": 5.0, "order_cost": 140.0},
    {"supplier_id": "SUP-105", "name": "Vanguard Apparel Mills", "lead_time_mean": 12, "lead_time_sd": 2.0, "order_cost": 65.0},
    {"supplier_id": "SUP-106", "name": "Cascade Outdoor Goods", "lead_time_mean": 10, "lead_time_sd": 1.8, "order_cost": 60.0},
    {"supplier_id": "SUP-107", "name": "Beacon Ergonomics Corp", "lead_time_mean": 18, "lead_time_sd": 3.0, "order_cost": 95.0},
    {"supplier_id": "SUP-108", "name": "Solstice Kitchenware Ltd", "lead_time_mean": 15, "lead_time_sd": 2.2, "order_cost": 75.0},
]

SKU_CATALOG = [
    # Top Revenue Drivers (Class A Candidates)
    {"sku_id": "SKU-001", "product_name": "Pro Active Noise-Cancelling Headphones", "category": "Consumer Electronics", "unit_price": 279.99, "cost_pct": 0.45, "supplier_id": "SUP-101", "base_weekly": 105.0, "trend": 0.15, "seasonality": "holiday", "holding_rate": 0.22},
    {"sku_id": "SKU-002", "product_name": "Smart Fitness GPS Watch Ultra", "category": "Consumer Electronics", "unit_price": 349.99, "cost_pct": 0.48, "supplier_id": "SUP-101", "base_weekly": 80.0, "trend": 0.18, "seasonality": "new_year", "holding_rate": 0.24},
    {"sku_id": "SKU-003", "product_name": "Executive Ergonomic High-Back Chair", "category": "Office & Productivity", "unit_price": 389.00, "cost_pct": 0.50, "supplier_id": "SUP-107", "base_weekly": 68.0, "trend": 0.10, "seasonality": "back_to_work", "holding_rate": 0.20},
    {"sku_id": "SKU-004", "product_name": "Dual-Motor Electric Standing Desk 60in", "category": "Office & Productivity", "unit_price": 499.00, "cost_pct": 0.52, "supplier_id": "SUP-107", "base_weekly": 52.0, "trend": 0.12, "seasonality": "back_to_work", "holding_rate": 0.20},
    {"sku_id": "SKU-005", "product_name": "Precision Barista Espresso Machine", "category": "Home & Kitchen", "unit_price": 449.50, "cost_pct": 0.46, "supplier_id": "SUP-108", "base_weekly": 56.0, "trend": 0.08, "seasonality": "holiday", "holding_rate": 0.22},
    {"sku_id": "SKU-006", "product_name": "Smart Auto-Empty Robotic Vacuum", "category": "Home & Kitchen", "unit_price": 399.99, "cost_pct": 0.47, "supplier_id": "SUP-108", "base_weekly": 62.0, "trend": 0.14, "seasonality": "holiday", "holding_rate": 0.22},
    {"sku_id": "SKU-007", "product_name": "Ultra Lightweight 4-Season Backpacking Tent", "category": "Outdoor & Sports", "unit_price": 289.00, "cost_pct": 0.42, "supplier_id": "SUP-106", "base_weekly": 74.0, "trend": 0.05, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-008", "product_name": "Carbon Fiber Road Cycling Helmet", "category": "Outdoor & Sports", "unit_price": 189.50, "cost_pct": 0.44, "supplier_id": "SUP-106", "base_weekly": 84.0, "trend": 0.06, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-009", "product_name": "Men's Waterproof Trail Running Shoe", "category": "Apparel & Footwear", "unit_price": 155.00, "cost_pct": 0.38, "supplier_id": "SUP-105", "base_weekly": 128.0, "trend": 0.10, "seasonality": "spring_summer", "holding_rate": 0.20},
    {"sku_id": "SKU-010", "product_name": "Women's Down Insulated Winter Parka", "category": "Apparel & Footwear", "unit_price": 249.00, "cost_pct": 0.40, "supplier_id": "SUP-105", "base_weekly": 92.0, "trend": 0.04, "seasonality": "winter", "holding_rate": 0.20},
    {"sku_id": "SKU-011", "product_name": "Custom Mechanical Gaming Keyboard RGB", "category": "Consumer Electronics", "unit_price": 169.99, "cost_pct": 0.42, "supplier_id": "SUP-104", "base_weekly": 108.0, "trend": 0.15, "seasonality": "holiday", "holding_rate": 0.22},
    {"sku_id": "SKU-012", "product_name": "4K Ultra-HD Streaming Conference Webcam", "category": "Consumer Electronics", "unit_price": 129.99, "cost_pct": 0.40, "supplier_id": "SUP-104", "base_weekly": 115.0, "trend": 0.08, "seasonality": "steady", "holding_rate": 0.20},
    {"sku_id": "SKU-013", "product_name": "Tri-Band WiFi 7 Mesh Router System", "category": "Consumer Electronics", "unit_price": 329.99, "cost_pct": 0.50, "supplier_id": "SUP-102", "base_weekly": 55.0, "trend": 0.14, "seasonality": "holiday", "holding_rate": 0.24},
    {"sku_id": "SKU-014", "product_name": "Heavy-Duty Dual Monitor Desk Mount", "category": "Office & Productivity", "unit_price": 119.50, "cost_pct": 0.38, "supplier_id": "SUP-107", "base_weekly": 106.0, "trend": 0.05, "seasonality": "steady", "holding_rate": 0.18},
    {"sku_id": "SKU-015", "product_name": "XL 8-Quart Digital Dual-Zone Air Fryer", "category": "Home & Kitchen", "unit_price": 179.99, "cost_pct": 0.45, "supplier_id": "SUP-108", "base_weekly": 104.0, "trend": 0.12, "seasonality": "holiday", "holding_rate": 0.22},
    {"sku_id": "SKU-016", "product_name": "Commercial Grade 14-Piece Cookware Set", "category": "Home & Kitchen", "unit_price": 299.00, "cost_pct": 0.48, "supplier_id": "SUP-108", "base_weekly": 48.0, "trend": 0.03, "seasonality": "holiday", "holding_rate": 0.20},
    {"sku_id": "SKU-017", "product_name": "Inflatable Stand Up Touring Paddleboard", "category": "Outdoor & Sports", "unit_price": 369.00, "cost_pct": 0.46, "supplier_id": "SUP-106", "base_weekly": 50.0, "trend": 0.09, "seasonality": "summer", "holding_rate": 0.20},
    {"sku_id": "SKU-018", "product_name": "Merino Wool Thermal Base Layer Top", "category": "Apparel & Footwear", "unit_price": 95.00, "cost_pct": 0.35, "supplier_id": "SUP-105", "base_weekly": 154.0, "trend": 0.06, "seasonality": "winter", "holding_rate": 0.18},
    {"sku_id": "SKU-019", "product_name": "High-Impact Recovery Massage Gun Pro", "category": "Consumer Electronics", "unit_price": 199.00, "cost_pct": 0.42, "supplier_id": "SUP-101", "base_weekly": 82.0, "trend": 0.10, "seasonality": "holiday", "holding_rate": 0.22},
    {"sku_id": "SKU-020", "product_name": "All-Weather Gore-Tex Hardshell Jacket", "category": "Apparel & Footwear", "unit_price": 289.00, "cost_pct": 0.44, "supplier_id": "SUP-105", "base_weekly": 60.0, "trend": 0.05, "seasonality": "fall_winter", "holding_rate": 0.20},
    
    # Class B SKUs (Medium Revenue)
    {"sku_id": "SKU-021", "product_name": "Wireless Charging Multi-Device Pad", "category": "Consumer Electronics", "unit_price": 59.99, "cost_pct": 0.40, "supplier_id": "SUP-103", "base_weekly": 168.0, "trend": 0.08, "seasonality": "holiday", "holding_rate": 0.20},
    {"sku_id": "SKU-022", "product_name": "Portable Waterproof Bluetooth Speaker", "category": "Consumer Electronics", "unit_price": 79.99, "cost_pct": 0.42, "supplier_id": "SUP-103", "base_weekly": 140.0, "trend": 0.06, "seasonality": "summer", "holding_rate": 0.20},
    {"sku_id": "SKU-023", "product_name": "Ergonomic Memory Foam Footrest", "category": "Office & Productivity", "unit_price": 45.00, "cost_pct": 0.36, "supplier_id": "SUP-107", "base_weekly": 158.0, "trend": 0.04, "seasonality": "steady", "holding_rate": 0.18},
    {"sku_id": "SKU-024", "product_name": "Dimmable ScreenBar Monitor Light", "category": "Office & Productivity", "unit_price": 89.00, "cost_pct": 0.40, "supplier_id": "SUP-107", "base_weekly": 98.0, "trend": 0.07, "seasonality": "winter", "holding_rate": 0.18},
    {"sku_id": "SKU-025", "product_name": "Borosilicate Glass Cold Brew Pitcher", "category": "Home & Kitchen", "unit_price": 38.50, "cost_pct": 0.32, "supplier_id": "SUP-108", "base_weekly": 182.0, "trend": 0.05, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-026", "product_name": "Japanese Damascus Santoku Chef Knife", "category": "Home & Kitchen", "unit_price": 85.00, "cost_pct": 0.38, "supplier_id": "SUP-108", "base_weekly": 95.0, "trend": 0.04, "seasonality": "holiday", "holding_rate": 0.20},
    {"sku_id": "SKU-027", "product_name": "Insulated Hydro Flask Stainless 32oz", "category": "Outdoor & Sports", "unit_price": 42.00, "cost_pct": 0.30, "supplier_id": "SUP-106", "base_weekly": 210.0, "trend": 0.07, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-028", "product_name": "Carbon Trekking Poles Pair", "category": "Outdoor & Sports", "unit_price": 68.00, "cost_pct": 0.36, "supplier_id": "SUP-106", "base_weekly": 105.0, "trend": 0.04, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-029", "product_name": "Breathable Quick-Dry Gym Shorts", "category": "Apparel & Footwear", "unit_price": 34.00, "cost_pct": 0.28, "supplier_id": "SUP-105", "base_weekly": 224.0, "trend": 0.05, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-030", "product_name": "Seamless High-Rise Compression Leggings", "category": "Apparel & Footwear", "unit_price": 54.00, "cost_pct": 0.32, "supplier_id": "SUP-105", "base_weekly": 175.0, "trend": 0.08, "seasonality": "new_year", "holding_rate": 0.18},
    {"sku_id": "SKU-031", "product_name": "Fast-Charging 65W GaN Wall Adapter", "category": "Consumer Electronics", "unit_price": 49.99, "cost_pct": 0.35, "supplier_id": "SUP-103", "base_weekly": 162.0, "trend": 0.09, "seasonality": "holiday", "holding_rate": 0.20},
    {"sku_id": "SKU-032", "product_name": "Anti-Fatigue Standing Desk Floor Mat", "category": "Office & Productivity", "unit_price": 62.00, "cost_pct": 0.38, "supplier_id": "SUP-107", "base_weekly": 112.0, "trend": 0.03, "seasonality": "steady", "holding_rate": 0.18},
    {"sku_id": "SKU-033", "product_name": "Cast Iron Dutch Oven 6-Quart Enameled", "category": "Home & Kitchen", "unit_price": 89.99, "cost_pct": 0.44, "supplier_id": "SUP-108", "base_weekly": 84.0, "trend": 0.04, "seasonality": "fall_winter", "holding_rate": 0.20},
    {"sku_id": "SKU-034", "product_name": "Ultra-Thick Non-Slip Yoga Mat 6mm", "category": "Outdoor & Sports", "unit_price": 48.00, "cost_pct": 0.34, "supplier_id": "SUP-106", "base_weekly": 147.0, "trend": 0.06, "seasonality": "new_year", "holding_rate": 0.18},
    {"sku_id": "SKU-035", "product_name": "Moisture-Wicking Athletic Running Socks 3pk", "category": "Apparel & Footwear", "unit_price": 22.00, "cost_pct": 0.25, "supplier_id": "SUP-105", "base_weekly": 294.0, "trend": 0.05, "seasonality": "steady", "holding_rate": 0.18},

    # Class C SKUs (Lower Volume / Long Tail)
    {"sku_id": "SKU-036", "product_name": "Braided USB-C to Lightning Cable 2m", "category": "Consumer Electronics", "unit_price": 19.99, "cost_pct": 0.25, "supplier_id": "SUP-103", "base_weekly": 196.0, "trend": -0.02, "seasonality": "holiday", "holding_rate": 0.18},
    {"sku_id": "SKU-037", "product_name": "Silicone Cable Organizer Clips 6pk", "category": "Office & Productivity", "unit_price": 12.50, "cost_pct": 0.20, "supplier_id": "SUP-103", "base_weekly": 245.0, "trend": 0.01, "seasonality": "steady", "holding_rate": 0.18},
    {"sku_id": "SKU-038", "product_name": "Bamboo Desk Organizer Drawer Tray", "category": "Office & Productivity", "unit_price": 28.00, "cost_pct": 0.30, "supplier_id": "SUP-107", "base_weekly": 77.0, "trend": 0.02, "seasonality": "back_to_work", "holding_rate": 0.18},
    {"sku_id": "SKU-039", "product_name": "Stainless Steel Measuring Spoons Set", "category": "Home & Kitchen", "unit_price": 16.99, "cost_pct": 0.24, "supplier_id": "SUP-108", "base_weekly": 126.0, "trend": 0.01, "seasonality": "holiday", "holding_rate": 0.18},
    {"sku_id": "SKU-040", "product_name": "Heat-Resistant Silicone Spatula Set", "category": "Home & Kitchen", "unit_price": 18.50, "cost_pct": 0.26, "supplier_id": "SUP-108", "base_weekly": 122.0, "trend": 0.01, "seasonality": "holiday", "holding_rate": 0.18},
    {"sku_id": "SKU-041", "product_name": "Aluminum Locking Carabiners 4pk", "category": "Outdoor & Sports", "unit_price": 14.99, "cost_pct": 0.22, "supplier_id": "SUP-106", "base_weekly": 140.0, "trend": 0.02, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-042", "product_name": "Quick-Dry Microfiber Camp Towel", "category": "Outdoor & Sports", "unit_price": 21.00, "cost_pct": 0.28, "supplier_id": "SUP-106", "base_weekly": 98.0, "trend": 0.03, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-043", "product_name": "Organic Cotton Crew Neck Tee", "category": "Apparel & Footwear", "unit_price": 26.00, "cost_pct": 0.30, "supplier_id": "SUP-105", "base_weekly": 154.0, "trend": 0.02, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-044", "product_name": "Thermal Fleece Beanie Hat", "category": "Apparel & Footwear", "unit_price": 18.00, "cost_pct": 0.25, "supplier_id": "SUP-105", "base_weekly": 112.0, "trend": 0.01, "seasonality": "winter", "holding_rate": 0.18},
    {"sku_id": "SKU-045", "product_name": "Stylus Pen for Capacitive Touchscreens", "category": "Consumer Electronics", "unit_price": 15.99, "cost_pct": 0.22, "supplier_id": "SUP-103", "base_weekly": 126.0, "trend": -0.01, "seasonality": "back_to_work", "holding_rate": 0.18},
    {"sku_id": "SKU-046", "product_name": "Non-Slip Mouse Pad with Wrist Rest", "category": "Office & Productivity", "unit_price": 14.99, "cost_pct": 0.25, "supplier_id": "SUP-107", "base_weekly": 133.0, "trend": 0.01, "seasonality": "steady", "holding_rate": 0.18},
    {"sku_id": "SKU-047", "product_name": "Aromatherapy Essential Oil Diffuser", "category": "Home & Kitchen", "unit_price": 29.99, "cost_pct": 0.32, "supplier_id": "SUP-108", "base_weekly": 84.0, "trend": 0.03, "seasonality": "holiday", "holding_rate": 0.20},
    {"sku_id": "SKU-048", "product_name": "Emergency Mylar Thermal Blankets 4pk", "category": "Outdoor & Sports", "unit_price": 11.99, "cost_pct": 0.20, "supplier_id": "SUP-106", "base_weekly": 105.0, "trend": 0.01, "seasonality": "fall_winter", "holding_rate": 0.18},
    {"sku_id": "SKU-049", "product_name": "Reflective Running Armband Phone Case", "category": "Apparel & Footwear", "unit_price": 16.50, "cost_pct": 0.25, "supplier_id": "SUP-105", "base_weekly": 91.0, "trend": 0.02, "seasonality": "summer", "holding_rate": 0.18},
    {"sku_id": "SKU-050", "product_name": "Screen Cleaning Spray & Cloth Kit", "category": "Consumer Electronics", "unit_price": 9.99, "cost_pct": 0.18, "supplier_id": "SUP-103", "base_weekly": 182.0, "trend": 0.00, "seasonality": "steady", "holding_rate": 0.18},
]

supplier_lookup = {s["supplier_id"]: s for s in SUPPLIERS}

def get_seasonality_factor(pattern, dt):
    doy = dt.timetuple().tm_yday
    month = dt.month
    
    if pattern == "holiday":
        if month in [11, 12]:
            return 1.45 + 0.35 * math.sin((doy - 300) / 60.0 * math.pi)
        elif month == 1:
            return 0.85
        return 0.95
    elif pattern == "summer":
        if month in [5, 6, 7, 8]:
            return 1.40 + 0.20 * math.sin((doy - 120) / 120.0 * math.pi)
        return 0.80
    elif pattern == "winter":
        if month in [11, 12, 1, 2]:
            return 1.50
        elif month in [6, 7, 8]:
            return 0.60
        return 0.90
    elif pattern == "spring_summer":
        if 3 <= month <= 8:
            return 1.25
        return 0.85
    elif pattern == "new_year":
        if month in [1, 2]:
            return 1.55
        elif month in [11, 12]:
            return 1.25
        return 0.90
    elif pattern == "back_to_work":
        if month in [8, 9, 1]:
            return 1.30
        return 0.95
    else:
        return 1.0

def generate_orders():
    start_date = datetime(2023, 1, 2) # First Monday of 2023
    num_weeks = 104
    
    raw_rows = []
    order_seq = 10000
    
    print(f"Synthesizing transaction dataset across {num_weeks} weeks for {len(SKU_CATALOG)} SKUs...")
    
    for week_idx in range(num_weeks):
        week_start = start_date + timedelta(weeks=week_idx)
        t_prog = week_idx / num_weeks
        
        for sku in SKU_CATALOG:
            s_mult = get_seasonality_factor(sku["seasonality"], week_start)
            trend_mult = 1.0 + (sku["trend"] * t_prog)
            expected_weekly_units = sku["base_weekly"] * s_mult * trend_mult
            
            # Stochastic weekly demand
            weekly_units = max(5, int(random.gauss(expected_weekly_units, math.sqrt(expected_weekly_units) * 1.2)))
            
            # Distribute weekly demand into 3-5 distinct customer orders within the week
            num_orders = random.randint(3, 5)
            supp = supplier_lookup[sku["supplier_id"]]
            unit_price = round(sku["unit_price"], 2)
            unit_cost = round(sku["unit_price"] * sku["cost_pct"], 2)
            order_cost = supp["order_cost"]
            holding_rate = sku["holding_rate"]
            
            units_remaining = weekly_units
            for order_i in range(num_orders):
                if order_i == num_orders - 1:
                    qty = units_remaining
                else:
                    qty = max(1, int(units_remaining / (num_orders - order_i) * random.uniform(0.7, 1.3)))
                    units_remaining = max(1, units_remaining - qty)
                
                order_seq += 1
                order_day_offset = random.randint(0, 6)
                order_date = week_start + timedelta(days=order_day_offset)
                cust_id = f"CUST-{random.randint(1000, 9999)}"
                lt = max(2, int(random.gauss(supp["lead_time_mean"], supp["lead_time_sd"])))
                
                raw_rows.append({
                    "order_id": f"ORD-{order_seq}",
                    "order_date": order_date.strftime("%Y-%m-%d"),
                    "customer_id": cust_id,
                    "sku_id": sku["sku_id"],
                    "product_name": sku["product_name"],
                    "category": sku["category"],
                    "unit_price": str(unit_price),
                    "unit_cost": str(unit_cost),
                    "quantity": str(qty),
                    "supplier_id": sku["supplier_id"],
                    "supplier_lead_time_days": str(lt),
                    "order_cost": str(order_cost),
                    "holding_cost_annual_rate": str(holding_rate)
                })

    print(f"Generated {len(raw_rows)} clean transaction rows.")
    
    # Inject deliberate dirty records to test SQL sanitization & deduplication
    print("Injecting dirty records (duplicates, missing keys, invalid quantities)...")
    
    # 1. Duplicate orders (approx 150 duplicate rows)
    duplicates = []
    for _ in range(150):
        sample = dict(random.choice(raw_rows))
        duplicates.append(sample)
    
    # 2. Corrupt rows
    corrupt_rows = [
        {"order_id": "", "order_date": "2024-05-10", "customer_id": "CUST-9999", "sku_id": "SKU-001", "product_name": "Pro Active Noise-Cancelling Headphones", "category": "Consumer Electronics", "unit_price": "279.99", "unit_cost": "125.99", "quantity": "2", "supplier_id": "SUP-101", "supplier_lead_time_days": "14", "order_cost": "85.0", "holding_cost_annual_rate": "0.22"},
        {"order_id": "ORD-CORRUPT-01", "order_date": "2024-05-11", "customer_id": "CUST-9998", "sku_id": "", "product_name": "Unknown", "category": "Office", "unit_price": "50.00", "unit_cost": "25.00", "quantity": "1", "supplier_id": "SUP-107", "supplier_lead_time_days": "10", "order_cost": "75.0", "holding_cost_annual_rate": "0.20"},
        {"order_id": "ORD-CORRUPT-02", "order_date": "2024-06-15", "customer_id": "CUST-9997", "sku_id": "SKU-002", "product_name": "Smart Fitness GPS Watch Ultra", "category": "Consumer Electronics", "unit_price": "349.99", "unit_cost": "167.99", "quantity": "-3", "supplier_id": "SUP-101", "supplier_lead_time_days": "14", "order_cost": "85.0", "holding_cost_annual_rate": "0.24"},
        {"order_id": "ORD-CORRUPT-03", "order_date": "2024-07-20", "customer_id": "CUST-9996", "sku_id": "SKU-003", "product_name": "Executive Ergonomic High-Back Chair", "category": "Office & Productivity", "unit_price": "0.00", "unit_cost": "194.50", "quantity": "1", "supplier_id": "SUP-107", "supplier_lead_time_days": "18", "order_cost": "95.0", "holding_cost_annual_rate": "0.20"},
        {"order_id": "ORD-CORRUPT-04", "order_date": "2024-08-01", "customer_id": "CUST-9995", "sku_id": "SKU-005", "product_name": "Precision Barista Espresso Machine", "category": "Home & Kitchen", "unit_price": "449.50", "unit_cost": "206.77", "quantity": "0", "supplier_id": "SUP-108", "supplier_lead_time_days": "15", "order_cost": "75.0", "holding_cost_annual_rate": "0.22"},
    ]
    
    all_raw = raw_rows + duplicates + corrupt_rows
    random.shuffle(all_raw)
    
    raw_csv_path = os.path.join(RAW_DATA_DIR, "supply_chain_raw.csv")
    fieldnames = [
        "order_id", "order_date", "customer_id", "sku_id", "product_name",
        "category", "unit_price", "unit_cost", "quantity", "supplier_id",
        "supplier_lead_time_days", "order_cost", "holding_cost_annual_rate"
    ]
    
    with open(raw_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_raw)
        
    print(f"Successfully saved raw orders to: {raw_csv_path} (Total: {len(all_raw)} records)")
    
    # Generate Inventory Master / Current On-Hand Stock
    inventory_rows = []
    for sku in SKU_CATALOG:
        supp = supplier_lookup[sku["supplier_id"]]
        lt_weeks = supp["lead_time_mean"] / 7.0
        weekly_demand = sku["base_weekly"]
        # Typical ROP roughly weekly_demand * lt_weeks + safety_stock
        approx_rop = weekly_demand * lt_weeks + 1.65 * (weekly_demand * 0.28) * math.sqrt(lt_weeks)
        
        # Configure on-hand stock strategically:
        # SKU-001, SKU-004, SKU-008, SKU-011, SKU-017 will be in High Stockout Risk (current_stock < ROP)
        # SKU-002, SKU-006, SKU-015, SKU-020 will be in Medium Stockout Risk
        # Others well-stocked
        if sku["sku_id"] in ["SKU-001", "SKU-004", "SKU-008", "SKU-011", "SKU-017"]:
            stock = int(approx_rop * random.uniform(0.40, 0.75)) # Deficit!
        elif sku["sku_id"] in ["SKU-002", "SKU-006", "SKU-015", "SKU-020"]:
            stock = int(approx_rop * random.uniform(0.95, 1.15)) # Borderline
        else:
            stock = int(approx_rop * random.uniform(1.40, 2.20)) # Safe
            
        inventory_rows.append({
            "sku_id": sku["sku_id"],
            "product_name": sku["product_name"],
            "category": sku["category"],
            "current_stock": stock,
            "unit_price": round(sku["unit_price"], 2),
            "unit_cost": round(sku["unit_price"] * sku["cost_pct"], 2),
            "supplier_id": sku["supplier_id"],
            "holding_cost_annual_rate": sku["holding_rate"],
            "order_cost": supp["order_cost"]
        })
        
    inv_csv_path = os.path.join(RAW_DATA_DIR, "inventory_master.csv")
    with open(inv_csv_path, mode="w", newline="", encoding="utf-8") as f:
        inv_fields = ["sku_id", "product_name", "category", "current_stock", "unit_price", "unit_cost", "supplier_id", "holding_cost_annual_rate", "order_cost"]
        writer = csv.DictWriter(f, fieldnames=inv_fields)
        writer.writeheader()
        writer.writerows(inventory_rows)
        
    print(f"Successfully saved inventory master to: {inv_csv_path}")

if __name__ == "__main__":
    generate_orders()
