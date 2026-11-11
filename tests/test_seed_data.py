import pytest
from database.seed_data import seed_database, SAMPLE_MEDICINES, SAMPLE_SALES
from config.db_config import get_db

def test_sample_data_structures():
    assert len(SAMPLE_MEDICINES) >= 10
    assert len(SAMPLE_SALES) >= 5
    for med in SAMPLE_MEDICINES:
        assert "medicine_id" in med
        assert "name" in med
        assert "category" in med
        assert "batches" in med
        assert isinstance(med["batches"], list)

def test_seed_database_execution():
    db = get_db("pharmatrack_test_db")
    result = seed_database(db, drop_existing=True)
    assert result["medicines_count"] >= 10
    assert result["sales_count"] >= 5
    
    # Verify in DB
    assert db.medicines.count_documents({}) >= 10
    assert db.sales.count_documents({}) >= 5
