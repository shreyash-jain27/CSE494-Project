import pytest
from database.schema_validation import (
    MEDICINES_SCHEMA,
    SALES_SCHEMA,
    apply_schema_validation
)
from config.db_config import get_db

def test_schema_definitions():
    assert "$jsonSchema" in MEDICINES_SCHEMA
    med_props = MEDICINES_SCHEMA["$jsonSchema"]["properties"]
    assert "batches" in med_props
    assert "category" in med_props
    assert "min_reorder_level" in med_props
    
    assert "$jsonSchema" in SALES_SCHEMA
    sales_props = SALES_SCHEMA["$jsonSchema"]["properties"]
    assert "items" in sales_props
    assert "total_amount" in sales_props
    assert "payment_mode" in sales_props

def test_apply_schema_validation():
    db = get_db("pharmatrack_test_db")
    result = apply_schema_validation(db)
    assert "medicines" in result
    assert "sales" in result
    assert result["medicines"] in ("created", "updated", "mocked")
    assert result["sales"] in ("created", "updated", "mocked")
