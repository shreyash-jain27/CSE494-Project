import os
import pytest
from config.db_config import get_db, get_connection_uri, get_client

def test_db_config_defaults():
    uri = get_connection_uri()
    assert "mongodb://" in uri
    db = get_db(db_name="pharmatrack_test_db")
    assert db.name == "pharmatrack_test_db"
    assert db is not None

def test_get_client():
    client = get_client()
    assert client is not None
