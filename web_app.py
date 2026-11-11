import os
import sys
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.db_config import get_db, is_mock_mode
from database.seed_data import seed_database
from database.schema_validation import apply_schema_validation
from core.crud import (
    create_medicine,
    get_medicine_by_id,
    search_medicines,
    add_batch_to_medicine,
    update_medicine,
    delete_medicine,
    delete_batch,
    process_sale
)
from core.aggregations import (
    get_near_expiry_batches,
    get_low_stock_medicines,
    get_category_sales_revenue,
    get_top_selling_medicines,
    get_inventory_health_facet
)
from cli_app import run_negative_validation_demo

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = "pharmatrack-secret-key-cse494"

def get_current_db():
    """Retrieve database handle respecting Flask app config."""
    db_name = app.config.get("DATABASE_NAME")
    return get_db(db_name)

@app.before_request
def ensure_seed():
    """Ensure database has initial sample data if empty."""
    db = get_current_db()
    if db.medicines.count_documents({}) == 0:
        seed_database(db, drop_existing=False)

def serialize_mongo(obj):
    """Recursively convert BSON/datetime/ObjectId objects to JSON-serializable structures."""
    if isinstance(obj, list):
        return [serialize_mongo(item) for item in obj]
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            if k == "_id":
                new_dict["_id"] = str(v)
            elif isinstance(v, (datetime, date)):
                new_dict[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                new_dict[k] = serialize_mongo(v)
            else:
                new_dict[k] = v
        return new_dict
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def api_status():
    db = get_current_db()
    total_meds = db.medicines.count_documents({})
    total_sales = db.sales.count_documents({})
    return jsonify({
        "status": "connected",
        "db_name": db.name,
        "is_mock": is_mock_mode(),
        "total_medicines": total_meds,
        "total_sales": total_sales
    })

@app.route("/api/medicines", methods=["GET", "POST"])
def api_medicines():
    db = get_current_db()
    if request.method == "GET":
        q = request.args.get("q", "").strip()
        cat = request.args.get("category", "").strip() or None
        results = search_medicines(db, query=q, category=cat)
        return jsonify(serialize_mongo(results))
    
    # POST
    payload = request.get_json() or {}
    try:
        med_id = create_medicine(db, payload)
        return jsonify({"status": "success", "medicine_id": med_id})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/medicines/<medicine_id>", methods=["GET", "PUT", "DELETE"])
def api_medicine_detail(medicine_id):
    db = get_current_db()
    if request.method == "GET":
        doc = get_medicine_by_id(db, medicine_id)
        if not doc:
            return jsonify({"status": "error", "error": "Not found"}), 404
        return jsonify(serialize_mongo(doc))
        
    elif request.method == "PUT":
        updates = request.get_json() or {}
        success = update_medicine(db, medicine_id, updates)
        return jsonify({"status": "success" if success else "error"})
        
    elif request.method == "DELETE":
        force = request.args.get("force", "false").lower() == "true"
        try:
            success = delete_medicine(db, medicine_id, force=force)
            return jsonify({"status": "success" if success else "error"})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/medicines/<medicine_id>/batch", methods=["POST"])
def api_add_batch(medicine_id):
    db = get_current_db()
    data = request.get_json() or {}
    try:
        exp_days = int(data.get("expiry_days", 180))
        batch_doc = {
            "batch_no": data.get("batch_no"),
            "mfg_date": datetime.utcnow(),
            "expiry_date": datetime.utcnow() + timedelta(days=exp_days),
            "quantity": int(data.get("quantity", 100)),
            "cost_price": float(data.get("cost_price", 10.0)),
            "selling_price": float(data.get("selling_price", 18.0))
        }
        success = add_batch_to_medicine(db, medicine_id, batch_doc)
        return jsonify({"status": "success" if success else "error"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/medicines/<medicine_id>/batch/<batch_no>", methods=["DELETE"])
def api_delete_batch(medicine_id, batch_no):
    db = get_current_db()
    success = delete_batch(db, medicine_id, batch_no)
    return jsonify({"status": "success" if success else "error"})

@app.route("/api/sales", methods=["GET", "POST"])
def api_sales():
    db = get_current_db()
    if request.method == "GET":
        sales = list(db.sales.find().sort("sale_date", -1).limit(20))
        return jsonify(serialize_mongo(sales))
        
    payload = request.get_json() or {}
    try:
        if "sale_date" in payload and isinstance(payload["sale_date"], str):
            payload["sale_date"] = datetime.fromisoformat(payload["sale_date"].replace("Z", "+00:00"))
        else:
            payload["sale_date"] = datetime.utcnow()
            
        res = process_sale(db, payload)
        return jsonify(serialize_mongo(res))
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/aggregations/expiry", methods=["GET"])
def api_agg_expiry():
    db = get_current_db()
    days = int(request.args.get("days", 60))
    alerts = get_near_expiry_batches(db, days_ahead=days)
    return jsonify(serialize_mongo(alerts))

@app.route("/api/aggregations/low-stock", methods=["GET"])
def api_agg_low_stock():
    db = get_current_db()
    results = get_low_stock_medicines(db)
    return jsonify(serialize_mongo(results))

@app.route("/api/aggregations/revenue", methods=["GET"])
def api_agg_revenue():
    db = get_current_db()
    results = get_category_sales_revenue(db)
    return jsonify(serialize_mongo(results))

@app.route("/api/aggregations/top-sellers", methods=["GET"])
def api_agg_top_sellers():
    db = get_current_db()
    limit = int(request.args.get("limit", 5))
    results = get_top_selling_medicines(db, limit=limit)
    return jsonify(serialize_mongo(results))

@app.route("/api/aggregations/facets", methods=["GET"])
def api_agg_facets():
    db = get_current_db()
    results = get_inventory_health_facet(db)
    return jsonify(serialize_mongo(results))

@app.route("/api/seed", methods=["POST"])
def api_seed():
    db = get_current_db()
    res = seed_database(db, drop_existing=True)
    return jsonify(res)

@app.route("/api/test-validation", methods=["POST"])
def api_test_validation():
    db = get_current_db()
    res = run_negative_validation_demo(db)
    return jsonify(res)

if __name__ == "__main__":
    db = get_db()
    if db.medicines.count_documents({}) == 0:
        seed_database(db, drop_existing=False)
        
    print("\n" + "=" * 65)
    print("   PHARMATRACK: Modern React-Style Web App Running!")
    print("   URL: http://127.0.0.1:5000")
    print("   CSE494 Intelligent NoSQL Databases - CA-2 Project")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
