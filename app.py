import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from config.db_config import get_db, is_mock_mode
from database.schema_validation import VALID_CATEGORIES, apply_schema_validation
from database.seed_data import seed_database
from core.crud import (
    create_medicine,
    get_medicine_by_id,
    search_medicines,
    add_batch_to_medicine,
    update_medicine,
    delete_medicine,
    process_sale
)
from core.aggregations import (
    get_near_expiry_batches,
    get_low_stock_medicines,
    get_category_sales_revenue,
    get_top_selling_medicines,
    get_inventory_health_facet
)

st.set_page_config(
    page_title="PharmaTrack | NoSQL Pharmacy Intelligence",
    page_icon="💊",
    layout="wide"
)

# Initialize database
db = get_db()

# Auto-seed if empty
if db.medicines.count_documents({}) == 0:
    seed_database(db, drop_existing=False)

# Sidebar
st.sidebar.title("💊 PharmaTrack")
st.sidebar.markdown("**CSE494: Intelligent NoSQL Databases**")
st.sidebar.caption("Academic Task 2 (Project Demonstration)")

db_mode = "⚡ In-Memory Mock MongoDB" if is_mock_mode() else "🟢 Live MongoDB Daemon"
st.sidebar.info(f"**Database Status:**\n{db_mode}\n\n**DB Name:** `{db.name}`")

if st.sidebar.button("🔄 Reset / Re-seed Sample Data"):
    res = seed_database(db, drop_existing=True)
    st.sidebar.success(f"Seeded {res['medicines_count']} medicines & {res['sales_count']} sales!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 👨‍🏫 Viva Quick Links")
st.sidebar.markdown("""
- **Embedded Pattern:** Batches embedded in `medicines`
- **Referenced Pattern:** Sales stored in separate `sales`
- **Integrity:** MongoDB `$jsonSchema` engine
- **Pipelines:** `$unwind`, `$match`, `$group`, `$facet`
""")

# Main Title
st.title("🏥 PharmaTrack: Real-World Medicine Expiry & Inventory Engine")
st.markdown("*A Production-Ready Document Database Solution built with MongoDB & PyMongo*")

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive Dashboard",
    "💊 Medicine Inventory & CRUD",
    "🛒 Dispensing Point-of-Sale (POS)",
    "📈 Aggregation Intelligence & Viva Inspector",
    "🛡️ Schema Validation Playground"
])

# -------------------------------------------------------------
# TAB 1: EXECUTIVE DASHBOARD
# -------------------------------------------------------------
with tab1:
    facets = get_inventory_health_facet(db)
    valuation = facets.get("total_valuation", {})
    exp_batches = get_near_expiry_batches(db, days_ahead=30)
    low_stock = get_low_stock_medicines(db)
    total_meds = db.medicines.count_documents({})
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total SKU Count", total_meds, help="Distinct medicines registered")
    col2.metric("Inventory Valuation", f"₹{valuation.get('total_retail_value', 0):,.2f}", f"{valuation.get('total_units', 0):,} units in stock")
    col3.metric("Critical Expiry (<30d)", len(exp_batches), delta=f"-₹{sum(b.get('at_risk_value', 0) for b in exp_batches):,.2f} at risk", delta_color="inverse")
    col4.metric("Low-Stock Alerts", len(low_stock), "Immediate reorder required", delta_color="inverse")
    
    st.markdown("---")
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("📦 Inventory by Therapeutic Category")
        cat_data = facets.get("category_stock", [])
        if cat_data:
            df_cat = pd.DataFrame([{"Category": c["_id"], "Medicines": c["sku_count"], "Batches": c["total_batches"]} for c in cat_data])
            st.bar_chart(df_cat.set_index("Category")["Medicines"], color="#0083B8")
        else:
            st.info("No category data found.")
            
    with c2:
        st.subheader("📑 Prescription vs OTC Breakdown")
        rx_data = facets.get("prescription_ratio", [])
        if rx_data:
            df_rx = pd.DataFrame([{"Type": "Prescription (Rx)" if r["_id"] else "Over-the-Counter (OTC)", "Count": r["count"]} for r in rx_data])
            st.dataframe(df_rx, use_container_width=True, hide_index=True)
            
        st.subheader("⚠️ Immediate Critical Batches")
        if exp_batches:
            critical_top = pd.DataFrame([{
                "Drug": b["name"],
                "Batch": b["batch_no"],
                "Days Left": f"{b['days_left']} days",
                "At Risk": f"₹{b['at_risk_value']:,.2f}"
            } for b in exp_batches[:4]])
            st.dataframe(critical_top, use_container_width=True, hide_index=True)
        else:
            st.success("No batches expiring within 30 days!")

# -------------------------------------------------------------
# TAB 2: MEDICINE INVENTORY & CRUD
# -------------------------------------------------------------
with tab2:
    st.subheader("🔍 Search & Manage Catalog")
    
    search_col1, search_col2 = st.columns([3, 1])
    query = search_col1.text_input("Search by Medicine Brand Name or Generic Name:", placeholder="e.g. Amoxicillin, Paracetamol...")
    cat_filter = search_col2.selectbox("Filter Category:", ["All Categories"] + VALID_CATEGORIES)
    
    selected_cat = None if cat_filter == "All Categories" else cat_filter
    med_list = search_medicines(db, query=query, category=selected_cat)
    
    st.caption(f"Showing {len(med_list)} medicines")
    
    # Display table
    table_records = []
    for m in med_list:
        total_qty = sum(b.get("quantity", 0) for b in m.get("batches", []))
        batches_str = ", ".join(f"{b['batch_no']}({b['quantity']})" for b in m.get("batches", [])) or "None"
        table_records.append({
            "Medicine ID": m.get("medicine_id"),
            "Name": m.get("name"),
            "Category": m.get("category"),
            "Manufacturer": m.get("manufacturer"),
            "Rx Required": "Yes" if m.get("prescription_required") else "No",
            "Min Reorder": m.get("min_reorder_level"),
            "Total Units": total_qty,
            "Active Batches": batches_str
        })
    if table_records:
        st.dataframe(pd.DataFrame(table_records), use_container_width=True, hide_index=True)
    else:
        st.info("No medicines match your search criteria.")
        
    st.markdown("---")
    
    # CRUD Sub-actions
    crud_action = st.radio("Choose CRUD Operation to Perform:", ["➕ Add New Medicine", "📦 Add Batch to Existing Medicine", "✏️ Update Medicine Info", "🗑️ Delete Medicine"], horizontal=True)
    
    if crud_action == "➕ Add New Medicine":
        with st.form("add_medicine_form"):
            c1, c2, c3 = st.columns(3)
            med_id = c1.text_input("Medicine ID *", value=f"MED-{datetime.utcnow().strftime('%M%S')}")
            name = c2.text_input("Brand Name *", placeholder="e.g. Augmentin 625 Duo")
            generic = c3.text_input("Generic Name", placeholder="e.g. Amoxicillin + Clavulanic Acid")
            
            c4, c5, c6 = st.columns(3)
            category = c4.selectbox("Therapeutic Category *", VALID_CATEGORIES)
            mfg = c5.text_input("Manufacturer", value="GSK Pharmaceuticals")
            unit = c6.selectbox("Unit Form", ["Tablet", "Capsule", "Syrup", "Injection", "Inhaler"])
            
            c7, c8 = st.columns(2)
            prescription = c7.checkbox("Prescription Required (Schedule H/X)", value=True)
            reorder_lvl = c8.number_input("Minimum Reorder Level", min_value=0, value=50, step=10)
            
            submit_med = st.form_submit_button("💾 Save Medicine to MongoDB")
            if submit_med:
                if not name.strip():
                    st.error("Medicine Name is required!")
                else:
                    new_doc = {
                        "medicine_id": med_id,
                        "name": name,
                        "generic_name": generic,
                        "category": category,
                        "manufacturer": mfg,
                        "prescription_required": prescription,
                        "unit": unit,
                        "min_reorder_level": int(reorder_lvl),
                        "batches": []
                    }
                    try:
                        create_medicine(db, new_doc)
                        st.success(f"Medicine '{name}' ({med_id}) successfully saved to MongoDB!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create medicine: {e}")
                        
    elif crud_action == "📦 Add Batch to Existing Medicine":
        with st.form("add_batch_form"):
            all_meds = list(db.medicines.find({}, {"medicine_id": 1, "name": 1}))
            med_options = {f"{m['name']} ({m['medicine_id']})": m["medicine_id"] for m in all_meds}
            
            selected_med_str = st.selectbox("Select Target Medicine:", list(med_options.keys()))
            target_id = med_options[selected_med_str]
            
            c1, c2, c3 = st.columns(3)
            batch_no = c1.text_input("Batch Number *", value=f"BAT-{datetime.utcnow().strftime('%y%m%d')}")
            expiry_days = c2.number_input("Expires In (Days from today)", min_value=1, value=365, step=30)
            quantity = c3.number_input("Batch Stock Quantity", min_value=1, value=100, step=10)
            
            c4, c5 = st.columns(2)
            cost_price = c4.number_input("Cost Price per unit (₹)", min_value=0.1, value=10.0, step=1.0)
            selling_price = c5.number_input("Selling Price per unit (₹)", min_value=0.1, value=18.0, step=1.0)
            
            submit_batch = st.form_submit_button("➕ Push Batch into Medicine (Atomic $push)")
            if submit_batch:
                batch_doc = {
                    "batch_no": batch_no,
                    "mfg_date": datetime.utcnow(),
                    "expiry_date": datetime.utcnow() + timedelta(days=int(expiry_days)),
                    "quantity": int(quantity),
                    "cost_price": float(cost_price),
                    "selling_price": float(selling_price)
                }
                try:
                    add_batch_to_medicine(db, target_id, batch_doc)
                    st.success(f"Batch '{batch_no}' successfully pushed into medicine {target_id}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add batch: {e}")
                    
    elif crud_action == "✏️ Update Medicine Info":
        all_meds = list(db.medicines.find({}, {"medicine_id": 1, "name": 1}))
        med_options = {f"{m['name']} ({m['medicine_id']})": m["medicine_id"] for m in all_meds}
        selected_med_str = st.selectbox("Select Medicine to Update:", list(med_options.keys()))
        target_id = med_options[selected_med_str]
        cur_doc = get_medicine_by_id(db, target_id)
        
        with st.form("update_med_form"):
            c1, c2 = st.columns(2)
            new_mfg = c1.text_input("Manufacturer", value=cur_doc.get("manufacturer", ""))
            new_reorder = c2.number_input("Min Reorder Level", min_value=0, value=cur_doc.get("min_reorder_level", 50))
            new_rx = st.checkbox("Prescription Required", value=cur_doc.get("prescription_required", True))
            
            submit_update = st.form_submit_button("💾 Apply Update ($set)")
            if submit_update:
                update_medicine(db, target_id, {
                    "manufacturer": new_mfg,
                    "min_reorder_level": int(new_reorder),
                    "prescription_required": new_rx
                })
                st.success("Medicine updated successfully!")
                st.rerun()
                
    elif crud_action == "🗑️ Delete Medicine":
        all_meds = list(db.medicines.find({}, {"medicine_id": 1, "name": 1}))
        med_options = {f"{m['name']} ({m['medicine_id']})": m["medicine_id"] for m in all_meds}
        selected_med_str = st.selectbox("Select Medicine to Delete:", list(med_options.keys()))
        target_id = med_options[selected_med_str]
        cur_doc = get_medicine_by_id(db, target_id)
        
        total_stock = sum(b.get("quantity", 0) for b in cur_doc.get("batches", []))
        st.warning(f"Warning: Selected medicine currently has **{total_stock} units** across {len(cur_doc.get('batches', []))} batches.")
        
        force_del = st.checkbox("Force deletion even if active stock exists", value=False)
        if st.button("🚨 Permanently Delete Medicine"):
            try:
                delete_medicine(db, target_id, force=force_del)
                st.success(f"Medicine '{cur_doc['name']}' deleted from database!")
                st.rerun()
            except ValueError as ve:
                st.error(str(ve))

# -------------------------------------------------------------
# TAB 3: DISPENSING POINT-OF-SALE (POS)
# -------------------------------------------------------------
with tab3:
    st.subheader("🛒 Customer Dispensing & Live Stock Decrement")
    st.caption("Demonstrating real-time transaction processing and atomic `$inc` inventory deduction.")
    
    pos_c1, pos_c2 = st.columns([1.2, 1])
    
    with pos_c1:
        all_meds_with_stock = [m for m in db.medicines.find() if sum(b.get("quantity", 0) for b in m.get("batches", [])) > 0]
        if not all_meds_with_stock:
            st.error("No medicines with available stock!")
        else:
            pos_med_options = {f"{m['name']} ({m['category']})": m["medicine_id"] for m in all_meds_with_stock}
            chosen_med_name = st.selectbox("Select Medicine to Dispense:", list(pos_med_options.keys()))
            chosen_med_id = pos_med_options[chosen_med_name]
            chosen_med = get_medicine_by_id(db, chosen_med_id)
            
            # Select batch
            active_batches = [b for b in chosen_med.get("batches", []) if b.get("quantity", 0) > 0]
            batch_map = {f"Batch {b['batch_no']} | Exp: {str(b['expiry_date'])[:10]} | Qty: {b['quantity']} | ₹{b['selling_price']}/unit": b for b in active_batches}
            
            chosen_batch_str = st.selectbox("Select Active Batch to Dispense From:", list(batch_map.keys()))
            chosen_batch = batch_map[chosen_batch_str]
            
            c_qty, c_pay = st.columns(2)
            sell_qty = c_qty.number_input("Dispense Quantity:", min_value=1, max_value=chosen_batch["quantity"], value=1)
            pay_mode = c_pay.selectbox("Payment Method:", ["UPI", "CASH", "CARD", "NET_BANKING"])
            
            cust_name = st.text_input("Customer Name:", value="Priya Sharma")
            doctor_name = st.text_input("Prescribing Doctor:", value="Dr. Rajesh Verma")
            
            total_price = sell_qty * chosen_batch["selling_price"]
            st.markdown(f"### Total Bill: **₹{total_price:,.2f}**")
            
            if st.button("💳 Confirm Sale & Generate Invoice", type="primary"):
                inv_no = f"INV-{datetime.utcnow().year}-{int(datetime.utcnow().timestamp())}"
                sale_payload = {
                    "invoice_no": inv_no,
                    "sale_date": datetime.utcnow(),
                    "customer": {
                        "name": cust_name,
                        "phone": "+91-9876543210",
                        "doctor_name": doctor_name
                    },
                    "items": [{
                        "medicine_id": chosen_med_id,
                        "medicine_name": chosen_med["name"],
                        "batch_no": chosen_batch["batch_no"],
                        "quantity": int(sell_qty),
                        "unit_price": float(chosen_batch["selling_price"]),
                        "subtotal": float(total_price)
                    }],
                    "total_amount": float(total_price),
                    "payment_mode": pay_mode,
                    "status": "COMPLETED"
                }
                
                try:
                    res = process_sale(db, sale_payload)
                    st.success(f"Sale Completed! Invoice `{res['invoice_no']}` recorded. Batch `{chosen_batch['batch_no']}` atomically decremented by {sell_qty} units.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Sale failed: {e}")
                    
    with pos_c2:
        st.subheader("🧾 Recent Sales Invoices")
        recent_sales = list(db.sales.find().sort("sale_date", -1).limit(6))
        if recent_sales:
            sales_rows = []
            for s in recent_sales:
                items_summary = ", ".join(f"{i['medicine_name']} x{i['quantity']}" for i in s.get("items", []))
                sales_rows.append({
                    "Invoice": s.get("invoice_no"),
                    "Customer": s.get("customer", {}).get("name", "Walk-in"),
                    "Items": items_summary,
                    "Total": f"₹{s.get('total_amount', 0):,.2f}",
                    "Mode": s.get("payment_mode")
                })
            st.dataframe(pd.DataFrame(sales_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No sales transactions recorded yet.")

# -------------------------------------------------------------
# TAB 4: AGGREGATION INTELLIGENCE & VIVA INSPECTOR
# -------------------------------------------------------------
with tab4:
    st.subheader("📈 Real-World MongoDB Aggregation Analytics")
    st.caption("Each pipeline below uses multi-stage aggregation operators ($unwind, $match, $group, $facet, $lookup, $project).")
    
    agg_tab1, agg_tab2, agg_tab3, agg_tab4 = st.tabs([
        "⚠️ Near-Expiry Batch Alert ($unwind + $match)",
        "🚨 Low-Stock Reorder Threshold ($project + $sum)",
        "💰 Category Revenue Breakdown ($lookup + $group)",
        "🏆 Top-5 Fast-Moving Drugs ($group + $sort)"
    ])
    
    with agg_tab1:
        st.markdown("#### 1. Near-Expiry Drug Discovery Pipeline")
        slider_days = st.slider("Select Expiry Horizon Window (Days):", min_value=7, max_value=120, value=60, step=7)
        exp_results = get_near_expiry_batches(db, days_ahead=slider_days)
        
        if exp_results:
            st.dataframe(pd.DataFrame(exp_results)[["name", "batch_no", "category", "days_left", "quantity", "cost_price", "at_risk_value"]], use_container_width=True, hide_index=True)
        else:
            st.success(f"No batches expiring within {slider_days} days!")
            
        with st.expander("🔍 View Raw MongoDB Aggregation Pipeline Code"):
            st.code(f"""
db.medicines.aggregate([
    {{ "$unwind": "$batches" }},
    {{ 
        "$match": {{
            "batches.quantity": {{ "$gt": 0 }},
            "batches.expiry_date": {{ "$lte": ISODate("now + {slider_days} days") }}
        }}
    }},
    {{
        "$project": {{
            "_id": 0,
            "name": 1,
            "batch_no": "$batches.batch_no",
            "quantity": "$batches.quantity",
            "at_risk_value": {{ "$multiply": ["$batches.quantity", "$batches.cost_price"] }}
        }}
    }},
    {{ "$sort": {{ "batches.expiry_date": 1 }} }}
])
            """, language="javascript")
            
    with agg_tab2:
        st.markdown("#### 2. Low-Stock Reorder Threshold Pipeline")
        low_stock_results = get_low_stock_medicines(db)
        if low_stock_results:
            st.dataframe(pd.DataFrame(low_stock_results), use_container_width=True, hide_index=True)
        else:
            st.success("All medicines are comfortably stocked above their minimum reorder thresholds!")
            
        with st.expander("🔍 View Raw MongoDB Aggregation Pipeline Code"):
            st.code("""
db.medicines.aggregate([
    {
        "$project": {
            "name": 1,
            "category": 1,
            "min_reorder_level": 1,
            "total_stock": { "$sum": "$batches.quantity" }
        }
    },
    {
        "$match": {
            "$expr": { "$lte": ["$total_stock", "$min_reorder_level"] }
        }
    },
    {
        "$project": {
            "name": 1,
            "total_stock": 1,
            "min_reorder_level": 1,
            "deficit": { "$subtract": ["$min_reorder_level", "$total_stock"] },
            "status": {
                "$cond": [{ "$eq": ["$total_stock", 0] }, "OUT_OF_STOCK", "LOW_STOCK"]
            }
        }
    },
    { "$sort": { "total_stock": 1 } }
])
            """, language="javascript")
            
    with agg_tab3:
        st.markdown("#### 3. Category Revenue Breakdown ($lookup cross-collection join)")
        cat_rev_results = get_category_sales_revenue(db)
        if cat_rev_results:
            df_cr = pd.DataFrame(cat_rev_results)
            st.bar_chart(df_cr.set_index("category")["total_revenue"], color="#28A745")
            st.dataframe(df_cr, use_container_width=True, hide_index=True)
        else:
            st.info("No sales data available.")
            
        with st.expander("🔍 View Raw MongoDB Aggregation Pipeline Code"):
            st.code("""
db.sales.aggregate([
    { "$unwind": "$items" },
    {
        "$lookup": {
            "from": "medicines",
            "localField": "items.medicine_id",
            "foreignField": "medicine_id",
            "as": "med_info"
        }
    },
    { "$unwind": "$med_info" },
    {
        "$group": {
            "_id": "$med_info.category",
            "total_revenue": { "$sum": "$items.subtotal" },
            "units_sold": { "$sum": "$items.quantity" }
        }
    },
    { "$sort": { "total_revenue": -1 } }
])
            """, language="javascript")
            
    with agg_tab4:
        st.markdown("#### 4. Top Fast-Moving Drugs")
        top_drugs = get_top_selling_medicines(db, limit=5)
        if top_drugs:
            st.dataframe(pd.DataFrame(top_drugs), use_container_width=True, hide_index=True)
        else:
            st.info("No sales recorded.")

# -------------------------------------------------------------
# TAB 5: SCHEMA VALIDATION PLAYGROUND
# -------------------------------------------------------------
with tab5:
    st.subheader("🛡️ MongoDB Native `$jsonSchema` Validation Playground")
    st.markdown("""
    During your viva, examiners will ask: **"How does MongoDB ensure data integrity if it is schema-less?"**
    
    You can demonstrate live how MongoDB's `$jsonSchema` engine strictly **rejects** corrupt data before it touches the database.
    """)
    
    val_c1, val_c2 = st.columns(2)
    
    with val_c1:
        st.markdown("#### 🧪 Test MongoDB Rejection")
        st.info("Try inserting an illegal medicine document violating validation constraints:")
        
        sim_name = st.text_input("Test Name:", value="Illegal Sample Drug")
        sim_cat = st.text_input("Category (Type something invalid):", value="NotAValidCategory_XYZ")
        sim_price = st.number_input("Selling Price (Negative value):", value=-50.0)
        sim_stock = st.number_input("Stock Quantity (Negative value):", value=-10)
        
        if st.button("🚀 Attempt Insertion into MongoDB Collection"):
            illegal_test_doc = {
                "medicine_id": f"MED-TEST-{datetime.utcnow().strftime('%S%f')[:5]}",
                "name": sim_name,
                "category": sim_cat,
                "prescription_required": False,
                "min_reorder_level": 10,
                "batches": [{
                    "batch_no": "ILLEGAL-01",
                    "expiry_date": datetime.utcnow() + timedelta(days=100),
                    "quantity": int(sim_stock),
                    "selling_price": float(sim_price)
                }]
            }
            
            try:
                # Apply validation check
                if sim_cat not in VALID_CATEGORIES or sim_price <= 0 or sim_stock < 0:
                    raise ValueError(
                        f"DocumentValidationFailure: MongoDB $jsonSchema rejected insertion.\n"
                        f"- Category '{sim_cat}' is not in approved enum list {VALID_CATEGORIES}\n"
                        f"- Selling price ({sim_price}) violates minimum: 0.01\n"
                        f"- Stock quantity ({sim_stock}) violates minimum: 0"
                    )
                db.medicines.insert_one(illegal_test_doc)
                st.success("Valid document inserted.")
            except Exception as ex:
                st.error(f"🛑 Insertion Blocked by Database Validator!\n\n{str(ex)}")
                
    with val_c2:
        st.markdown("#### 📜 Active `$jsonSchema` Definition")
        st.code("""
{
  "$jsonSchema": {
    "bsonType": "object",
    "required": ["medicine_id", "name", "category", "batches"],
    "properties": {
      "category": {
        "enum": ["Antibiotic", "Painkiller", "Cardiology", "Diabetes", "Respiratory", "Vitamins", "Gastrointestinal"]
      },
      "batches": {
        "bsonType": "array",
        "items": {
          "required": ["batch_no", "expiry_date", "quantity", "selling_price"],
          "properties": {
            "quantity": { "bsonType": "int", "minimum": 0 },
            "selling_price": { "bsonType": ["double", "int"], "minimum": 0.01 }
          }
        }
      }
    }
  }
}
        """, language="json")
