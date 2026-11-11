import pytest
from datetime import datetime
from config.db_config import get_db
from database.seed_data import seed_database
from core.aggregations import (
    get_near_expiry_batches,
    get_low_stock_medicines,
    get_category_sales_revenue,
    get_top_selling_medicines,
    get_inventory_health_facet
)

@pytest.fixture(scope="module")
def seeded_db():
    db = get_db("pharmatrack_test_db")
    seed_database(db, drop_existing=True)
    return db

def test_near_expiry_batches(seeded_db):
    alerts = get_near_expiry_batches(seeded_db, days_ahead=60)
    assert isinstance(alerts, list)
    assert len(alerts) > 0
    # First item should be the one closest to expiry
    assert "batch_no" in alerts[0]
    assert "days_left" in alerts[0]
    assert "at_risk_value" in alerts[0]
    assert alerts[0]["days_left"] <= 60

def test_low_stock_medicines(seeded_db):
    low_stock = get_low_stock_medicines(seeded_db)
    assert isinstance(low_stock, list)
    assert len(low_stock) > 0
    for item in low_stock:
        assert item["total_stock"] <= item["min_reorder_level"]
        assert "deficit" in item

def test_category_sales_revenue(seeded_db):
    cat_sales = get_category_sales_revenue(seeded_db)
    assert isinstance(cat_sales, list)
    assert len(cat_sales) > 0
    # Highest revenue category first
    assert "category" in cat_sales[0]
    assert "total_revenue" in cat_sales[0]
    assert cat_sales[0]["total_revenue"] >= cat_sales[-1]["total_revenue"]

def test_top_selling_medicines(seeded_db):
    top_5 = get_top_selling_medicines(seeded_db, limit=5)
    assert isinstance(top_5, list)
    assert len(top_5) <= 5
    assert len(top_5) > 0
    assert "medicine_name" in top_5[0]
    assert "units_sold" in top_5[0]

def test_inventory_health_facet(seeded_db):
    health = get_inventory_health_facet(seeded_db)
    assert isinstance(health, dict)
    assert "category_stock" in health
    assert "prescription_ratio" in health
    assert "total_valuation" in health
