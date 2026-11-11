import pytest
from cli_app import (
    format_medicine_table,
    format_expiry_table,
    format_low_stock_table,
    format_sales_revenue_table,
    run_negative_validation_demo
)
from config.db_config import get_db
from database.seed_data import seed_database

def test_cli_table_formatters():
    sample_meds = [{
        "medicine_id": "MED-101",
        "name": "Paracetamol 650mg",
        "category": "Painkiller",
        "prescription_required": False,
        "min_reorder_level": 50,
        "batches": [{"batch_no": "B1", "quantity": 20, "selling_price": 2.5}]
    }]
    med_table = format_medicine_table(sample_meds)
    assert "Paracetamol 650mg" in med_table
    assert "MED-101" in med_table
    
    sample_exp = [{
        "name": "Amoxicillin 500mg",
        "batch_no": "AMX-01",
        "category": "Antibiotic",
        "days_left": 15,
        "quantity": 30,
        "at_risk_value": 165.0
    }]
    exp_table = format_expiry_table(sample_exp)
    assert "Amoxicillin" in exp_table
    assert "AMX-01" in exp_table

def test_negative_validation_demo():
    db = get_db("pharmatrack_test_db")
    seed_database(db, drop_existing=True)
    res = run_negative_validation_demo(db)
    assert res["expected_error_caught"] is True
    assert "error_type" in res
