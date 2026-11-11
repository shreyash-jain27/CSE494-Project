from pymongo.collection import Collection
from datetime import datetime
import re


def create_medicine(db, data: dict) -> str:
    """
    Insert a new medicine document into the `medicines` collection.
    Validates mandatory fields and initial structure.
    """
    if "medicine_id" not in data or "name" not in data or "category" not in data:
        raise ValueError(
            "Missing mandatory medicine fields: medicine_id, name, or category")

    if "batches" not in data:
        data["batches"] = []
    if "created_at" not in data:
        data["created_at"] = datetime.utcnow()

    db.medicines.insert_one(data)
    return data["medicine_id"]


def get_medicine_by_id(db, medicine_id: str) -> dict | None:
    """
    Retrieve a single medicine document by its unique medicine_id.
    """
    return db.medicines.find_one({"medicine_id": medicine_id})


def search_medicines(db, query: str = "", category: str = None) -> list[dict]:
    """
    Search medicines by matching name or generic_name regex and optional category filter.
    """
    filter_criteria = {}
    if query:
        escaped = re.escape(query)
        filter_criteria["$or"] = [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"generic_name": {"$regex": escaped, "$options": "i"}}
        ]
    if category:
        filter_criteria["category"] = category

    return list(db.medicines.find(filter_criteria))


def add_batch_to_medicine(db, medicine_id: str, batch: dict) -> bool:
    """
    Add a new manufacturing batch to a medicine using MongoDB's atomic `$push` operator.
    """
    required_keys = ["batch_no", "expiry_date", "quantity", "selling_price"]
    for k in required_keys:
        if k not in batch:
            raise ValueError(f"Missing required batch field: {k}")

    if batch["quantity"] < 0:
        raise ValueError("Batch quantity cannot be negative")
    if batch["selling_price"] <= 0:
        raise ValueError("Batch selling price must be greater than zero")

    res = db.medicines.update_one(
        {"medicine_id": medicine_id},
        {"$push": {"batches": batch}}
    )
    return res.modified_count > 0


def update_medicine(db, medicine_id: str, updates: dict) -> bool:
    """
    Update top-level medicine fields using MongoDB's `$set` operator.
    """
    # Prevent overwriting medicine_id or batches directly via this method
    safe_updates = {k: v for k, v in updates.items() if k not in [
        "medicine_id", "batches"]}
    if not safe_updates:
        return False

    res = db.medicines.update_one(
        {"medicine_id": medicine_id},
        {"$set": safe_updates}
    )
    return res.modified_count > 0


def update_batch_stock(db, medicine_id: str, batch_no: str, delta: int) -> bool:
    """
    Increment or decrement stock quantity of a specific batch atomically using `$inc`.
    """
    res = db.medicines.update_one(
        {"medicine_id": medicine_id, "batches.batch_no": batch_no},
        {"$inc": {"batches.$.quantity": delta}}
    )
    return res.modified_count > 0


def delete_batch(db, medicine_id: str, batch_no: str) -> bool:
    """
    Remove an expired or decommissioned batch from a medicine document using `$pull`.
    """
    res = db.medicines.update_one(
        {"medicine_id": medicine_id},
        {"$pull": {"batches": {"batch_no": batch_no}}}
    )
    return res.modified_count > 0


def delete_medicine(db, medicine_id: str, force: bool = False) -> bool:
    """
    Delete a medicine from the database.
    If force is False, blocks deletion if the medicine still has stock > 0 across any batch.
    """
    med = get_medicine_by_id(db, medicine_id)
    if not med:
        return False

    total_stock = sum(b.get("quantity", 0) for b in med.get("batches", []))
    if total_stock > 0 and not force:
        raise ValueError(
            f"Cannot delete medicine '{med['name']}' with active stock ({total_stock} units). Use force=True to override.")

    res = db.medicines.delete_one({"medicine_id": medicine_id})
    return res.deleted_count > 0


def process_sale(db, sale_data: dict) -> dict:
    """
    Process a customer sale:
    1. Validates that required invoice items exist and have sufficient stock.
    2. Atomically decrements batch quantities using `$inc`.
    3. Inserts the transaction document into `sales` collection.
    """
    items = sale_data.get("items", [])
    if not items:
        raise ValueError("Sale must contain at least one item")

    # Check inventory availability for every item
    for item in items:
        med = get_medicine_by_id(db, item["medicine_id"])
        if not med:
            raise ValueError(
                f"Medicine with ID '{item['medicine_id']}' not found")

        matched_batch = next(
            (b for b in med.get("batches", []) if b["batch_no"] == item["batch_no"]), None)
        if not matched_batch:
            raise ValueError(
                f"Batch '{item['batch_no']}' not found for medicine '{item['medicine_name']}'")

        if matched_batch["quantity"] < item["quantity"]:
            raise ValueError(
                f"Insufficient stock for {item['medicine_name']} batch {item['batch_no']}. "
                f"Available: {matched_batch['quantity']}, Requested: {item['quantity']}"
            )

    # Atomically deduct stock from each batch
    for item in items:
        update_batch_stock(db, item["medicine_id"],
                           item["batch_no"], -item["quantity"])

    # Record transaction invoice in sales collection
    db.sales.insert_one(sale_data)

    return {
        "status": "success",
        "invoice_no": sale_data["invoice_no"],
        "items_count": len(items),
        "total_amount": sale_data["total_amount"]
    }
