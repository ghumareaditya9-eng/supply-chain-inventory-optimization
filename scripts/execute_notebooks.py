#!/usr/bin/env python3
"""
execute_notebooks.py
Executes all code cells in each notebook to verify top-to-bottom reproducibility
and saves the executed outputs directly into the .ipynb files.
"""

import os
import json
import traceback
import matplotlib
matplotlib.use('Agg') # Headless non-blocking backend for headless execution

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOKS_DIR = os.path.join(BASE_DIR, "notebooks")

notebooks = [
    "01_eda.ipynb",
    "02_forecasting.ipynb",
    "03_inventory_optimization.ipynb"
]

def execute_notebook(nb_name):
    nb_path = os.path.join(NOTEBOOKS_DIR, nb_name)
    print(f"\nExecuting {nb_name}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    global_scope = {
        "__file__": nb_path,
        "__name__": "__main__"
    }
    
    orig_cwd = os.getcwd()
    os.chdir(NOTEBOOKS_DIR)
    
    execution_count = 1
    has_error = False
    
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            source_code = "".join(cell.get("source", []))
            cell["execution_count"] = execution_count
            cell["outputs"] = []
            try:
                exec(source_code, global_scope)
                execution_count += 1
            except Exception as e:
                has_error = True
                print(f" [ERROR] in cell {execution_count} of {nb_name}: {e}")
                traceback.print_exc()
                cell["outputs"].append({
                    "output_type": "error",
                    "ename": type(e).__name__,
                    "evalue": str(e),
                    "traceback": traceback.format_exc().splitlines()
                })
                break
                
    os.chdir(orig_cwd)
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
        
    if not has_error:
        print(f" -> [PASSED] {nb_name} executed top-to-bottom with 0 errors.")
    return not has_error

def main():
    print("=" * 60)
    print("RUNNING TOP-TO-BOTTOM NOTEBOOK REPRODUCIBILITY TEST")
    print("=" * 60)
    
    all_passed = True
    for nb in notebooks:
        ok = execute_notebook(nb)
        if not ok:
            all_passed = False
            
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL NOTEBOOKS EXECUTED CLEANLY WITH ZERO ERRORS!")
    else:
        print("SOME NOTEBOOKS ENCOUNTERED ERRORS.")
    print("=" * 60)

if __name__ == "__main__":
    main()
