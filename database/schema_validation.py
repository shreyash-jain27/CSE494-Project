import pymongo
from pymongo.errors import OperationFailure

# Allowed Medicine Categories
VALID_CATEGORIES = [
    "Antibiotic",
    "Painkiller",
    "Cardiology",
    "Diabetes",
    "Respiratory",
    "Vitamins",
    "Gastrointestinal"
]

# Allowed Payment Modes
VALID_PAYMENT_MODES = [
    "CASH",
    "UPI",
    "CARD",
    "NET_BANKING"
]

# Allowed Sale Statuses
VALID_SALE_STATUSES = [
    "COMPLETED",
    "REFUNDED",
    "CANCELLED"
]

# JSON Schema for `medicines` Collection
MEDICINES_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "medicine_id",
            "name",
            "category",
            "prescription_required",
            "min_reorder_level",
            "batches"
        ],
        "properties": {
            "medicine_id": {
                "bsonType": "string",
                "pattern": "^MED-[A-Z0-9-]+$",
                "description": "Unique medicine identifier string, e.g. MED-1001"
            },
            "name": {
                "bsonType": "string",
                "minLength": 2,
                "description": "Commercial brand name of the drug"
            },
            "generic_name": {
                "bsonType": "string",
                "description": "Active chemical constituent"
            },
            "category": {
                "enum": VALID_CATEGORIES,
                "description": "Therapeutic class from approved category list"
            },
            "manufacturer": {
                "bsonType": "string",
                "description": "Pharmaceutical manufacturer name"
            },
            "prescription_required": {
                "bsonType": "bool",
                "description": "Whether a valid medical prescription is mandatory"
            },
            "unit": {
                "bsonType": "string",
                "description": "Unit of measurement (Tablet, Capsule, Syrup, Strip)"
            },
            "min_reorder_level": {
                "bsonType": "int",
                "minimum": 0,
                "description": "Threshold quantity below which stock alert triggers"
            },
            "batches": {
                "bsonType": "array",
                "description": "List of active manufacturing batches",
                "items": {
                    "bsonType": "object",
                    "required": [
                        "batch_no",
                        "expiry_date",
                        "quantity",
                        "selling_price"
                    ],
                    "properties": {
                        "batch_no": {
                            "bsonType": "string",
                            "description": "Batch serial identifier"
                        },
                        "mfg_date": {
                            "bsonType": "date",
                            "description": "Date of manufacture"
                        },
                        "expiry_date": {
                            "bsonType": "date",
                            "description": "Batch expiration date"
                        },
                        "quantity": {
                            "bsonType": "int",
                            "minimum": 0,
                            "description": "Current stock count of this batch"
                        },
                        "cost_price": {
                            "bsonType": ["double", "int", "decimal"],
                            "minimum": 0,
                            "description": "Procurement cost per unit"
                        },
                        "selling_price": {
                            "bsonType": ["double", "int", "decimal"],
                            "minimum": 0.01,
                            "description": "Retail price per unit (must be > 0)"
                        }
                    }
                }
            }
        }
    }
}

# JSON Schema for `sales` Collection
SALES_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "invoice_no",
            "sale_date",
            "items",
            "total_amount",
            "payment_mode",
            "status"
        ],
        "properties": {
            "invoice_no": {
                "bsonType": "string",
                "pattern": "^INV-[A-Za-z0-9-]+$",
                "description": "Invoice number format, e.g. INV-2026-0001"
            },
            "sale_date": {
                "bsonType": "date",
                "description": "Transaction timestamp"
            },
            "customer": {
                "bsonType": "object",
                "properties": {
                    "name": {"bsonType": "string"},
                    "phone": {"bsonType": "string"},
                    "doctor_name": {"bsonType": "string"}
                }
            },
            "items": {
                "bsonType": "array",
                "minItems": 1,
                "description": "List of medicines dispensed (at least 1 required)",
                "items": {
                    "bsonType": "object",
                    "required": [
                        "medicine_id",
                        "medicine_name",
                        "batch_no",
                        "quantity",
                        "unit_price",
                        "subtotal"
                    ],
                    "properties": {
                        "medicine_id": {"bsonType": "string"},
                        "medicine_name": {"bsonType": "string"},
                        "batch_no": {"bsonType": "string"},
                        "quantity": {
                            "bsonType": "int",
                            "minimum": 1,
                            "description": "Quantity sold must be >= 1"
                        },
                        "unit_price": {
                            "bsonType": ["double", "int", "decimal"],
                            "minimum": 0.01
                        },
                        "subtotal": {
                            "bsonType": ["double", "int", "decimal"],
                            "minimum": 0.01
                        }
                    }
                }
            },
            "total_amount": {
                "bsonType": ["double", "int", "decimal"],
                "minimum": 0.01,
                "description": "Total invoice bill (must be > 0)"
            },
            "payment_mode": {
                "enum": VALID_PAYMENT_MODES,
                "description": "Mode of payment"
            },
            "status": {
                "enum": VALID_SALE_STATUSES,
                "description": "Status of invoice"
            }
        }
    }
}

def apply_schema_validation(db) -> dict:
    """
    Apply JSON Schema validation rules to `medicines` and `sales` collections.
    Supports both live MongoDB (via create_collection or collMod) and mock DBs.
    """
    results = {}
    schemas = {
        "medicines": MEDICINES_SCHEMA,
        "sales": SALES_SCHEMA
    }
    
    # Check if mock client
    if hasattr(db.client, "_mongomock") or "mongomock" in db.client.__class__.__module__:
        for col_name in schemas:
            if col_name not in db.list_collection_names():
                db.create_collection(col_name)
            results[col_name] = "mocked"
        return results

    for col_name, schema in schemas.items():
        try:
            if col_name in db.list_collection_names():
                # Update existing collection validator
                db.command({
                    "collMod": col_name,
                    "validator": schema,
                    "validationLevel": "moderate",
                    "validationAction": "error"
                })
                results[col_name] = "updated"
            else:
                # Create collection with validator
                db.create_collection(
                    col_name,
                    validator=schema,
                    validationLevel="moderate",
                    validationAction="error"
                )
                results[col_name] = "created"
        except OperationFailure as e:
            results[col_name] = f"error: {str(e)}"
            
    return results
