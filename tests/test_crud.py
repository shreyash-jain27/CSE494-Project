import pytest
from datetime import datetime, timedelta
from config.db_config import get_db
from core.crud import (
    create_medicine,
    get_medicine_by_id,
    search_medicines,
    add_batch_to_medicine,
    update_medicine,
    update_batch_stock,
    delete_batch,
    delete_medicine,
    process_sale
)

@pytest.fixture
def clean_db():
    db = get_db("pharmatrack_test_db")
    db.medicines.delete_many({})
    db.sales.delete_many({})
    return db

def test_medicine_create_and_read(clean_db):
    med = {
        "medicine_id": "MED-9001",
        "name": "Cefixime 200mg",
        "generic_name": "Cefixime",
        "category": "Antibiotic",
        "manufacturer": "Cipla",
        "prescription_required": True,
        "unit": "Tablet",
        "min_reorder_level": 30,
        "batches": []
    }
    med_id = create_medicine(clean_db, med)
    assert med_id == "MED-9001"
    
    fetched = get_medicine_by_id(clean_db, "MED-9001")
    assert fetched is not None
    assert fetched["name"] == "Cefixime 200mg"
    assert fetched["category"] == "Antibiotic"

def test_add_batch_and_update(clean_db):
    med = {
        "medicine_id": "MED-9002",
        "name": "Cetirizine 10mg",
        "generic_name": "Cetirizine Di-HCl",
        "category": "Respiratory",
        "manufacturer": "Dr. Reddy's",
        "prescription_required": False,
        "unit": "Tablet",
        "min_reorder_level": 25,
        "batches": []
    }
    create_medicine(clean_db, med)
    
    now = datetime.utcnow()
    batch = {
        "batch_no": "CET-01",
        "mfg_date": now - timedelta(days=30),
        "expiry_date": now + timedelta(days=300),
        "quantity": 100,
        "cost_price": 1.0,
        "selling_price": 2.5
    }
    added = add_batch_to_medicine(clean_db, "MED-9002", batch)
    assert added is True
    
    fetched = get_medicine_by_id(clean_db, "MED-9002")
    assert len(fetched["batches"]) == 1
    assert fetched["batches"][0]["batch_no"] == "CET-01"
    
    # Update medicine fields
    updated = update_medicine(clean_db, "MED-9002", {"manufacturer": "Sun Pharma"})
    assert updated is True
    assert get_medicine_by_id(clean_db, "MED-9002")["manufacturer"] == "Sun Pharma"

def test_search_medicines(clean_db):
    med1 = {
        "medicine_id": "MED-9003",
        "name": "Paracetamol 500mg",
        "generic_name": "Acetaminophen",
        "category": "Painkiller",
        "manufacturer": "GSK",
        "prescription_required": False,
        "unit": "Tablet",
        "min_reorder_level": 50,
        "batches": []
    }
    create_medicine(clean_db, med1)
    
    results = search_medicines(clean_db, query="para")
    assert len(results) >= 1
    assert results[0]["medicine_id"] == "MED-9003"
    
    results_cat = search_medicines(clean_db, category="Painkiller")
    assert len(results_cat) >= 1

def test_process_sale_success_and_insufficient_stock(clean_db):
    now = datetime.utcnow()
    med = {
        "medicine_id": "MED-9004",
        "name": "Omeprazole 20mg",
        "generic_name": "Omeprazole",
        "category": "Gastrointestinal",
        "manufacturer": "Abbott",
        "prescription_required": False,
        "unit": "Capsule",
        "min_reorder_level": 20,
        "batches": [{
            "batch_no": "OMP-01",
            "mfg_date": now - timedelta(days=50),
            "expiry_date": now + timedelta(days=200),
            "quantity": 15,
            "cost_price": 2.0,
            "selling_price": 4.0
        }]
    }
    create_medicine(clean_db, med)
    
    # Successful sale
    sale_data = {
        "invoice_no": "INV-2026-9001",
        "sale_date": now,
        "customer": {"name": "Test User", "phone": "9999999999", "doctor_name": "Dr. Self"},
        "items": [{
            "medicine_id": "MED-9004",
            "medicine_name": "Omeprazole 20mg",
            "batch_no": "OMP-01",
            "quantity": 5,
            "unit_price": 4.0,
            "subtotal": 20.0
        }],
        "total_amount": 20.0,
        "payment_mode": "UPI",
        "status": "COMPLETED"
    }
    res = process_sale(clean_db, sale_data)
    assert res["status"] == "success"
    
    # Check that batch stock decremented from 15 to 10
    updated_med = get_medicine_by_id(clean_db, "MED-9004")
    assert updated_med["batches"][0]["quantity"] == 10
    
    # Sale with insufficient stock (asking 20 when only 10 left)
    failing_sale = {
        "invoice_no": "INV-2026-9002",
        "sale_date": now,
        "customer": {"name": "Test User 2", "phone": "9999999999", "doctor_name": "Dr. Self"},
        "items": [{
            "medicine_id": "MED-9004",
            "medicine_name": "Omeprazole 20mg",
            "batch_no": "OMP-01",
            "quantity": 20,
            "unit_price": 4.0,
            "subtotal": 80.0
        }],
        "total_amount": 80.0,
        "payment_mode": "CASH",
        "status": "COMPLETED"
    }
    with pytest.raises(ValueError, match="Insufficient stock"):
        process_sale(clean_db, failing_sale)

def test_delete_batch_and_medicine(clean_db):
    now = datetime.utcnow()
    med = {
        "medicine_id": "MED-9005",
        "name": "Temporary Med",
        "generic_name": "Temp",
        "category": "Vitamins",
        "manufacturer": "TempLab",
        "prescription_required": False,
        "unit": "Tablet",
        "min_reorder_level": 10,
        "batches": [{
            "batch_no": "TMP-01",
            "mfg_date": now - timedelta(days=20),
            "expiry_date": now + timedelta(days=100),
            "quantity": 10,
            "cost_price": 1.0,
            "selling_price": 2.0
        }]
    }
    create_medicine(clean_db, med)
    
    # Deleting medicine with active stock without force should raise error
    with pytest.raises(ValueError, match="active stock"):
        delete_medicine(clean_db, "MED-9005", force=False)
        
    # Delete batch
    assert delete_batch(clean_db, "MED-9005", "TMP-01") is True
    assert len(get_medicine_by_id(clean_db, "MED-9005")["batches"]) == 0
    
    # Now delete medicine should succeed
    assert delete_medicine(clean_db, "MED-9005", force=False) is True
    assert get_medicine_by_id(clean_db, "MED-9005") is None
