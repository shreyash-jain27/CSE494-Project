import pytest
import json
from config.db_config import get_db
from database.seed_data import seed_database

@pytest.fixture
def client():
    from web_app import app
    app.config["TESTING"] = True
    app.config["DATABASE_NAME"] = "pharmatrack_web_test_db"
    with app.test_client() as client:
        db = get_db("pharmatrack_web_test_db")
        seed_database(db, drop_existing=True)
        yield client

def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "db_name" in data
    assert "total_medicines" in data

def test_api_medicines_list(client):
    res = client.get("/api/medicines")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) >= 10

def test_api_aggregations_expiry(client):
    res = client.get("/api/aggregations/expiry?days=60")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)

def test_api_aggregations_facets(client):
    res = client.get("/api/aggregations/facets")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_valuation" in data

def test_api_negative_validation(client):
    res = client.post("/api/test-validation")
    assert res.status_code == 200
    data = res.get_json()
    assert data["expected_error_caught"] is True
