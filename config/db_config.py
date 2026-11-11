import os
import sys
from dotenv import load_dotenv
import pymongo
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

load_dotenv()

DEFAULT_URI = "mongodb://localhost:27017/"
DEFAULT_DB_NAME = "pharmatrack_db"

_CLIENT_INSTANCE = None
_IS_MOCK = False

def get_connection_uri(uri: str = None) -> str:
    """Return the active MongoDB connection URI."""
    if uri:
        return uri
    return os.getenv("MONGODB_URI", DEFAULT_URI)

def get_client(uri: str = None, timeout_ms: int = 1500):
    """
    Connect to MongoDB. If the local/remote server is unavailable,
    gracefully fall back to an in-memory mongomock client so testing
    and offline execution never crash.
    """
    global _CLIENT_INSTANCE, _IS_MOCK
    if _CLIENT_INSTANCE is not None:
        return _CLIENT_INSTANCE
        
    target_uri = get_connection_uri(uri)
    
    try:
        client = pymongo.MongoClient(
            target_uri,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms
        )
        # Verify connection by triggering a quick ping
        client.admin.command('ping')
        _CLIENT_INSTANCE = client
        _IS_MOCK = False
        return client
    except (ServerSelectionTimeoutError, ConnectionFailure, Exception):
        import mongomock
        _CLIENT_INSTANCE = mongomock.MongoClient()
        _IS_MOCK = True
        return _CLIENT_INSTANCE

def is_mock_mode() -> bool:
    """Return True if currently running on in-memory mock MongoDB."""
    return _IS_MOCK

def get_db(db_name: str = None, uri: str = None):
    """Return the database handle for PharmaTrack."""
    client = get_client(uri)
    name = db_name or os.getenv("DATABASE_NAME", DEFAULT_DB_NAME)
    return client[name]
