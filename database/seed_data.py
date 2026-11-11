from datetime import datetime, timedelta
from database.schema_validation import apply_schema_validation

# Helper for relative dates
NOW = datetime.utcnow()

SAMPLE_MEDICINES = [
    {
        "medicine_id": "MED-1001",
        "name": "Amoxicillin 500mg",
        "generic_name": "Amoxicillin Trihydrate",
        "category": "Antibiotic",
        "manufacturer": "Cipla Ltd",
        "prescription_required": True,
        "unit": "Capsule",
        "min_reorder_level": 50,
        "batches": [
            {
                "batch_no": "AMX-2401",
                "mfg_date": NOW - timedelta(days=300),
                "expiry_date": NOW + timedelta(days=20),  # Expiring soon (<30 days!)
                "quantity": 35,
                "cost_price": 5.50,
                "selling_price": 9.00
            },
            {
                "batch_no": "AMX-2402",
                "mfg_date": NOW - timedelta(days=60),
                "expiry_date": NOW + timedelta(days=360),
                "quantity": 120,
                "cost_price": 5.50,
                "selling_price": 9.00
            }
        ]
    },
    {
        "medicine_id": "MED-1002",
        "name": "Azithromycin 500mg",
        "generic_name": "Azithromycin",
        "category": "Antibiotic",
        "manufacturer": "Sun Pharma",
        "prescription_required": True,
        "unit": "Tablet",
        "min_reorder_level": 40,
        "batches": [
            {
                "batch_no": "AZI-2401",
                "mfg_date": NOW - timedelta(days=180),
                "expiry_date": NOW + timedelta(days=45),  # Warning zone (<60 days)
                "quantity": 25,
                "cost_price": 14.00,
                "selling_price": 22.50
            }
        ]
    },
    {
        "medicine_id": "MED-1003",
        "name": "Dolo 650mg",
        "generic_name": "Paracetamol",
        "category": "Painkiller",
        "manufacturer": "Micro Labs",
        "prescription_required": False,
        "unit": "Tablet",
        "min_reorder_level": 100,
        "batches": [
            {
                "batch_no": "DLO-2401",
                "mfg_date": NOW - timedelta(days=90),
                "expiry_date": NOW + timedelta(days=500),
                "quantity": 300,
                "cost_price": 1.20,
                "selling_price": 2.50
            },
            {
                "batch_no": "DLO-2309",
                "mfg_date": NOW - timedelta(days=400),
                "expiry_date": NOW + timedelta(days=14),  # Critical expiry (<15 days!)
                "quantity": 18,
                "cost_price": 1.10,
                "selling_price": 2.50
            }
        ]
    },
    {
        "medicine_id": "MED-1004",
        "name": "Ibuprofen 400mg",
        "generic_name": "Ibuprofen",
        "category": "Painkiller",
        "manufacturer": "Abbott",
        "prescription_required": False,
        "unit": "Tablet",
        "min_reorder_level": 60,
        "batches": [
            {
                "batch_no": "IBU-2401",
                "mfg_date": NOW - timedelta(days=120),
                "expiry_date": NOW + timedelta(days=400),
                "quantity": 40,  # Below reorder level (40 <= 60) -> Low stock alert!
                "cost_price": 2.00,
                "selling_price": 3.80
            }
        ]
    },
    {
        "medicine_id": "MED-1005",
        "name": "Atorvastatin 20mg",
        "generic_name": "Atorvastatin Calcium",
        "category": "Cardiology",
        "manufacturer": "Dr. Reddy's",
        "prescription_required": True,
        "unit": "Tablet",
        "min_reorder_level": 50,
        "batches": [
            {
                "batch_no": "ATV-2401",
                "mfg_date": NOW - timedelta(days=150),
                "expiry_date": NOW + timedelta(days=28),  # Expiring soon (<30 days!)
                "quantity": 45,
                "cost_price": 8.00,
                "selling_price": 14.00
            },
            {
                "batch_no": "ATV-2402",
                "mfg_date": NOW - timedelta(days=30),
                "expiry_date": NOW + timedelta(days=550),
                "quantity": 150,
                "cost_price": 8.00,
                "selling_price": 14.00
            }
        ]
    },
    {
        "medicine_id": "MED-1006",
        "name": "Amlodipine 5mg",
        "generic_name": "Amlodipine Besylate",
        "category": "Cardiology",
        "manufacturer": "Torrent Pharma",
        "prescription_required": True,
        "unit": "Tablet",
        "min_reorder_level": 40,
        "batches": [
            {
                "batch_no": "AML-2401",
                "mfg_date": NOW - timedelta(days=200),
                "expiry_date": NOW + timedelta(days=300),
                "quantity": 15,  # Below reorder level (15 <= 40) -> Low stock alert!
                "cost_price": 1.50,
                "selling_price": 3.00
            }
        ]
    },
    {
        "medicine_id": "MED-1007",
        "name": "Metformin 500mg",
        "generic_name": "Metformin Hydrochloride",
        "category": "Diabetes",
        "manufacturer": "USV Pvt Ltd",
        "prescription_required": True,
        "unit": "Tablet",
        "min_reorder_level": 120,
        "batches": [
            {
                "batch_no": "MET-2401",
                "mfg_date": NOW - timedelta(days=100),
                "expiry_date": NOW + timedelta(days=450),
                "quantity": 250,
                "cost_price": 1.80,
                "selling_price": 3.50
            }
        ]
    },
    {
        "medicine_id": "MED-1008",
        "name": "Glimepiride 2mg",
        "generic_name": "Glimepiride",
        "category": "Diabetes",
        "manufacturer": "Sanofi",
        "prescription_required": True,
        "unit": "Tablet",
        "min_reorder_level": 50,
        "batches": [
            {
                "batch_no": "GLM-2401",
                "mfg_date": NOW - timedelta(days=220),
                "expiry_date": NOW + timedelta(days=25),  # Expiring soon (<30 days!)
                "quantity": 30,
                "cost_price": 4.00,
                "selling_price": 7.50
            }
        ]
    },
    {
        "medicine_id": "MED-1009",
        "name": "Montelukast 10mg",
        "generic_name": "Montelukast Sodium",
        "category": "Respiratory",
        "manufacturer": "Mankind",
        "prescription_required": True,
        "unit": "Tablet",
        "min_reorder_level": 40,
        "batches": [
            {
                "batch_no": "MON-2401",
                "mfg_date": NOW - timedelta(days=90),
                "expiry_date": NOW + timedelta(days=380),
                "quantity": 80,
                "cost_price": 6.00,
                "selling_price": 11.00
            }
        ]
    },
    {
        "medicine_id": "MED-1010",
        "name": "Salbutamol Inhaler",
        "generic_name": "Salbutamol 100mcg",
        "category": "Respiratory",
        "manufacturer": "Cipla Ltd",
        "prescription_required": True,
        "unit": "Inhaler",
        "min_reorder_level": 20,
        "batches": [
            {
                "batch_no": "SAL-2401",
                "mfg_date": NOW - timedelta(days=150),
                "expiry_date": NOW + timedelta(days=320),
                "quantity": 8,  # Below reorder level (8 <= 20) -> Low stock!
                "cost_price": 95.00,
                "selling_price": 145.00
            }
        ]
    },
    {
        "medicine_id": "MED-1011",
        "name": "Vitamin D3 60K",
        "generic_name": "Cholecalciferol",
        "category": "Vitamins",
        "manufacturer": "Cadila",
        "prescription_required": False,
        "unit": "Capsule",
        "min_reorder_level": 50,
        "batches": [
            {
                "batch_no": "VIT-2401",
                "mfg_date": NOW - timedelta(days=110),
                "expiry_date": NOW + timedelta(days=500),
                "quantity": 180,
                "cost_price": 15.00,
                "selling_price": 28.00
            }
        ]
    },
    {
        "medicine_id": "MED-1012",
        "name": "Pantoprazole 40mg",
        "generic_name": "Pantoprazole Sodium",
        "category": "Gastrointestinal",
        "manufacturer": "Alkem Labs",
        "prescription_required": False,
        "unit": "Tablet",
        "min_reorder_level": 80,
        "batches": [
            {
                "batch_no": "PAN-2401",
                "mfg_date": NOW - timedelta(days=140),
                "expiry_date": NOW + timedelta(days=400),
                "quantity": 220,
                "cost_price": 3.50,
                "selling_price": 6.80
            }
        ]
    }
]

SAMPLE_SALES = [
    {
        "invoice_no": "INV-2026-0001",
        "sale_date": NOW - timedelta(days=5, hours=3),
        "customer": {
            "name": "Aarav Patel",
            "phone": "+91-9820011223",
            "doctor_name": "Dr. V. Mehta"
        },
        "items": [
            {
                "medicine_id": "MED-1001",
                "medicine_name": "Amoxicillin 500mg",
                "batch_no": "AMX-2401",
                "quantity": 10,
                "unit_price": 9.00,
                "subtotal": 90.00
            },
            {
                "medicine_id": "MED-1003",
                "medicine_name": "Dolo 650mg",
                "batch_no": "DLO-2401",
                "quantity": 15,
                "unit_price": 2.50,
                "subtotal": 37.50
            }
        ],
        "total_amount": 127.50,
        "payment_mode": "UPI",
        "status": "COMPLETED"
    },
    {
        "invoice_no": "INV-2026-0002",
        "sale_date": NOW - timedelta(days=4, hours=6),
        "customer": {
            "name": "Pooja Hegde",
            "phone": "+91-9876543210",
            "doctor_name": "Dr. S. Kulkarni"
        },
        "items": [
            {
                "medicine_id": "MED-1002",
                "medicine_name": "Azithromycin 500mg",
                "batch_no": "AZI-2401",
                "quantity": 5,
                "unit_price": 22.50,
                "subtotal": 112.50
            },
            {
                "medicine_id": "MED-1012",
                "medicine_name": "Pantoprazole 40mg",
                "batch_no": "PAN-2401",
                "quantity": 10,
                "unit_price": 6.80,
                "subtotal": 68.00
            }
        ],
        "total_amount": 180.50,
        "payment_mode": "CARD",
        "status": "COMPLETED"
    },
    {
        "invoice_no": "INV-2026-0003",
        "sale_date": NOW - timedelta(days=3, hours=2),
        "customer": {
            "name": "Rohan Gupta",
            "phone": "+91-9911223344",
            "doctor_name": "Dr. A. Verma"
        },
        "items": [
            {
                "medicine_id": "MED-1005",
                "medicine_name": "Atorvastatin 20mg",
                "batch_no": "ATV-2401",
                "quantity": 30,
                "unit_price": 14.00,
                "subtotal": 420.00
            },
            {
                "medicine_id": "MED-1007",
                "medicine_name": "Metformin 500mg",
                "batch_no": "MET-2401",
                "quantity": 60,
                "unit_price": 3.50,
                "subtotal": 210.00
            }
        ],
        "total_amount": 630.00,
        "payment_mode": "UPI",
        "status": "COMPLETED"
    },
    {
        "invoice_no": "INV-2026-0004",
        "sale_date": NOW - timedelta(days=2, hours=1),
        "customer": {
            "name": "Simran Kaur",
            "phone": "+91-9833445566",
            "doctor_name": "Dr. R. Joshi"
        },
        "items": [
            {
                "medicine_id": "MED-1010",
                "medicine_name": "Salbutamol Inhaler",
                "batch_no": "SAL-2401",
                "quantity": 2,
                "unit_price": 145.00,
                "subtotal": 290.00
            }
        ],
        "total_amount": 290.00,
        "payment_mode": "CASH",
        "status": "COMPLETED"
    },
    {
        "invoice_no": "INV-2026-0005",
        "sale_date": NOW - timedelta(days=1, hours=5),
        "customer": {
            "name": "Vikram Seth",
            "phone": "+91-9744556677",
            "doctor_name": "Self"
        },
        "items": [
            {
                "medicine_id": "MED-1011",
                "medicine_name": "Vitamin D3 60K",
                "batch_no": "VIT-2401",
                "quantity": 4,
                "unit_price": 28.00,
                "subtotal": 112.00
            },
            {
                "medicine_id": "MED-1003",
                "medicine_name": "Dolo 650mg",
                "batch_no": "DLO-2401",
                "quantity": 20,
                "unit_price": 2.50,
                "subtotal": 50.00
            }
        ],
        "total_amount": 162.00,
        "payment_mode": "UPI",
        "status": "COMPLETED"
    },
    {
        "invoice_no": "INV-2026-0006",
        "sale_date": NOW - timedelta(hours=8),
        "customer": {
            "name": "Meera Nambiar",
            "phone": "+91-9655443322",
            "doctor_name": "Dr. S. Kulkarni"
        },
        "items": [
            {
                "medicine_id": "MED-1008",
                "medicine_name": "Glimepiride 2mg",
                "batch_no": "GLM-2401",
                "quantity": 20,
                "unit_price": 7.50,
                "subtotal": 150.00
            }
        ],
        "total_amount": 150.00,
        "payment_mode": "NET_BANKING",
        "status": "COMPLETED"
    }
]

def seed_database(db, drop_existing: bool = True) -> dict:
    """
    Seed the database with schema validation and realistic sample data.
    """
    apply_schema_validation(db)
    
    if drop_existing:
        db.medicines.delete_many({})
        db.sales.delete_many({})
        
    med_insert_result = db.medicines.insert_many(SAMPLE_MEDICINES)
    sales_insert_result = db.sales.insert_many(SAMPLE_SALES)
    
    return {
        "status": "success",
        "medicines_count": len(med_insert_result.inserted_ids),
        "sales_count": len(sales_insert_result.inserted_ids)
    }

if __name__ == "__main__":
    from config.db_config import get_db
    database = get_db()
    res = seed_database(database)
    print(f"Seeding completed successfully: {res['medicines_count']} medicines, {res['sales_count']} sales inserted.")
