from datetime import datetime, timedelta

def get_near_expiry_batches(db, days_ahead: int = 60) -> list[dict]:
    """
    MongoDB Aggregation Pipeline: Identify batches expiring within `days_ahead` days.
    
    Stages:
    1. $unwind: Deconstruct the `batches` array into individual documents.
    2. $match: Filter batches with quantity > 0 and expiry_date <= target_date.
    3. $project: Compute at-risk financial value and extract fields.
    4. $sort: Sort ascending by expiry_date (most urgent first).
    """
    now = datetime.utcnow()
    target_date = now + timedelta(days=days_ahead)
    
    pipeline = [
        {"$unwind": "$batches"},
        {
            "$match": {
                "batches.quantity": {"$gt": 0},
                "batches.expiry_date": {"$lte": target_date}
            }
        },
        {
            "$project": {
                "_id": 0,
                "medicine_id": 1,
                "name": 1,
                "category": 1,
                "batch_no": "$batches.batch_no",
                "expiry_date": "$batches.expiry_date",
                "quantity": "$batches.quantity",
                "cost_price": "$batches.cost_price",
                "selling_price": "$batches.selling_price",
                "at_risk_value": {"$multiply": ["$batches.quantity", "$batches.cost_price"]}
            }
        },
        {"$sort": {"expiry_date": 1}}
    ]
    
    try:
        results = list(db.medicines.aggregate(pipeline))
    except Exception:
        # Fallback for mock environments without full aggregation support
        results = []
        for med in db.medicines.find():
            for b in med.get("batches", []):
                if b.get("quantity", 0) > 0 and b.get("expiry_date") and b["expiry_date"] <= target_date:
                    results.append({
                        "medicine_id": med["medicine_id"],
                        "name": med["name"],
                        "category": med["category"],
                        "batch_no": b["batch_no"],
                        "expiry_date": b["expiry_date"],
                        "quantity": b["quantity"],
                        "cost_price": b.get("cost_price", 0),
                        "selling_price": b.get("selling_price", 0),
                        "at_risk_value": round(b["quantity"] * b.get("cost_price", 0), 2)
                    })
        results.sort(key=lambda x: x["expiry_date"])
        
    for r in results:
        delta = (r["expiry_date"] - now).days
        r["days_left"] = max(0, delta)
        r["at_risk_value"] = round(r.get("at_risk_value", 0), 2)
        
    return results

def get_low_stock_medicines(db) -> list[dict]:
    """
    MongoDB Aggregation Pipeline: Identify medicines whose total stock <= min_reorder_level.
    
    Stages:
    1. $project: Compute `total_stock` across all embedded batches via $sum.
    2. $match: Filter where total_stock <= min_reorder_level.
    3. $project: Compute deficit and urgency status.
    4. $sort: Sort ascending by total_stock.
    """
    pipeline = [
        {
            "$project": {
                "_id": 0,
                "medicine_id": 1,
                "name": 1,
                "category": 1,
                "min_reorder_level": 1,
                "total_stock": {"$sum": "$batches.quantity"}
            }
        },
        {
            "$match": {
                "$expr": {"$lte": ["$total_stock", "$min_reorder_level"]}
            }
        },
        {
            "$project": {
                "medicine_id": 1,
                "name": 1,
                "category": 1,
                "min_reorder_level": 1,
                "total_stock": 1,
                "deficit": {"$subtract": ["$min_reorder_level", "$total_stock"]},
                "status": {
                    "$cond": [{"$eq": ["$total_stock", 0]}, "OUT_OF_STOCK", "REORDER_REQUIRED"]
                }
            }
        },
        {"$sort": {"total_stock": 1}}
    ]
    
    try:
        return list(db.medicines.aggregate(pipeline))
    except Exception:
        results = []
        for med in db.medicines.find():
            total = sum(b.get("quantity", 0) for b in med.get("batches", []))
            reorder = med.get("min_reorder_level", 0)
            if total <= reorder:
                results.append({
                    "medicine_id": med["medicine_id"],
                    "name": med["name"],
                    "category": med["category"],
                    "min_reorder_level": reorder,
                    "total_stock": total,
                    "deficit": max(0, reorder - total),
                    "status": "OUT_OF_STOCK" if total == 0 else "REORDER_REQUIRED"
                })
        results.sort(key=lambda x: x["total_stock"])
        return results

def get_category_sales_revenue(db) -> list[dict]:
    """
    MongoDB Aggregation Pipeline: Sales revenue breakdown grouped by therapeutic category.
    
    Stages:
    1. $unwind: Deconstruct sales `items`.
    2. $lookup: Join with `medicines` collection to pull drug category.
    3. $unwind: Unpack joined `medicine_info`.
    4. $group: Group by category, calculating revenue, units sold, and orders.
    5. $sort: Sort descending by total_revenue.
    """
    pipeline = [
        {"$unwind": "$items"},
        {
            "$lookup": {
                "from": "medicines",
                "localField": "items.medicine_id",
                "foreignField": "medicine_id",
                "as": "med_info"
            }
        },
        {"$unwind": "$med_info"},
        {
            "$group": {
                "_id": "$med_info.category",
                "total_revenue": {"$sum": "$items.subtotal"},
                "units_sold": {"$sum": "$items.quantity"},
                "transaction_count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "category": "$_id",
                "total_revenue": {"$round": ["$total_revenue", 2]},
                "units_sold": 1,
                "transaction_count": 1
            }
        },
        {"$sort": {"total_revenue": -1}}
    ]
    
    try:
        return list(db.sales.aggregate(pipeline))
    except Exception:
        # Fallback grouping
        cat_map = {}
        med_lookup = {m["medicine_id"]: m["category"] for m in db.medicines.find()}
        for sale in db.sales.find():
            for item in sale.get("items", []):
                cat = med_lookup.get(item["medicine_id"], "General")
                if cat not in cat_map:
                    cat_map[cat] = {"total_revenue": 0.0, "units_sold": 0, "transaction_count": 0}
                cat_map[cat]["total_revenue"] += item.get("subtotal", 0.0)
                cat_map[cat]["units_sold"] += item.get("quantity", 0)
                cat_map[cat]["transaction_count"] += 1
                
        out = [{"category": k, "total_revenue": round(v["total_revenue"], 2), "units_sold": v["units_sold"], "transaction_count": v["transaction_count"]} for k, v in cat_map.items()]
        out.sort(key=lambda x: x["total_revenue"], reverse=True)
        return out

def get_top_selling_medicines(db, limit: int = 5) -> list[dict]:
    """
    MongoDB Aggregation Pipeline: Identify top-selling medicines by volume.
    
    Stages:
    1. $unwind: Deconstruct sales `items`.
    2. $group: Group by medicine_name, summing total quantity and revenue.
    3. $sort: Sort descending by units_sold.
    4. $limit: Return top N best-sellers.
    """
    pipeline = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.medicine_name",
                "medicine_id": {"$first": "$items.medicine_id"},
                "units_sold": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": "$items.subtotal"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "medicine_name": "$_id",
                "medicine_id": 1,
                "units_sold": 1,
                "total_revenue": {"$round": ["$total_revenue", 2]}
            }
        },
        {"$sort": {"units_sold": -1}},
        {"$limit": limit}
    ]
    
    try:
        return list(db.sales.aggregate(pipeline))
    except Exception:
        totals = {}
        for sale in db.sales.find():
            for item in sale.get("items", []):
                name = item["medicine_name"]
                if name not in totals:
                    totals[name] = {
                        "medicine_name": name,
                        "medicine_id": item["medicine_id"],
                        "units_sold": 0,
                        "total_revenue": 0.0
                    }
                totals[name]["units_sold"] += item.get("quantity", 0)
                totals[name]["total_revenue"] += item.get("subtotal", 0.0)
        out = list(totals.values())
        for o in out:
            o["total_revenue"] = round(o["total_revenue"], 2)
        out.sort(key=lambda x: x["units_sold"], reverse=True)
        return out[:limit]

def get_inventory_health_facet(db) -> dict:
    """
    MongoDB Aggregation Pipeline: Multi-faceted dashboard using `$facet`.
    Simultaneously computes:
    - category_stock: SKUs and batches per category.
    - prescription_ratio: Count of Rx vs OTC medicines.
    - total_valuation: Total units, cost valuation, and retail valuation.
    """
    pipeline = [
        {
            "$facet": {
                "category_stock": [
                    {
                        "$group": {
                            "_id": "$category",
                            "sku_count": {"$sum": 1},
                            "total_batches": {"$sum": {"$size": "$batches"}}
                        }
                    },
                    {"$sort": {"sku_count": -1}}
                ],
                "prescription_ratio": [
                    {
                        "$group": {
                            "_id": "$prescription_required",
                            "count": {"$sum": 1}
                        }
                    }
                ],
                "total_valuation": [
                    {"$unwind": "$batches"},
                    {
                        "$group": {
                            "_id": None,
                            "total_cost_value": {"$sum": {"$multiply": ["$batches.quantity", "$batches.cost_price"]}},
                            "total_retail_value": {"$sum": {"$multiply": ["$batches.quantity", "$batches.selling_price"]}},
                            "total_units": {"$sum": "$batches.quantity"}
                        }
                    }
                ]
            }
        }
    ]
    
    try:
        raw = list(db.medicines.aggregate(pipeline))
        if raw and len(raw) > 0:
            facet_res = raw[0]
            val = facet_res.get("total_valuation", [])
            val_doc = val[0] if val else {"total_cost_value": 0, "total_retail_value": 0, "total_units": 0}
            return {
                "category_stock": facet_res.get("category_stock", []),
                "prescription_ratio": facet_res.get("prescription_ratio", []),
                "total_valuation": {
                    "total_cost_value": round(val_doc.get("total_cost_value", 0), 2),
                    "total_retail_value": round(val_doc.get("total_retail_value", 0), 2),
                    "total_units": val_doc.get("total_units", 0)
                }
            }
    except Exception:
        pass
        
    # Python fallback
    cat_stock = {}
    rx_count = {True: 0, False: 0}
    cost_val = 0.0
    retail_val = 0.0
    total_units = 0
    
    for med in db.medicines.find():
        cat = med.get("category", "General")
        cat_stock[cat] = cat_stock.get(cat, {"sku_count": 0, "total_batches": 0})
        cat_stock[cat]["sku_count"] += 1
        cat_stock[cat]["total_batches"] += len(med.get("batches", []))
        
        rx_count[med.get("prescription_required", False)] += 1
        
        for b in med.get("batches", []):
            qty = b.get("quantity", 0)
            cost = b.get("cost_price", 0)
            sell = b.get("selling_price", 0)
            total_units += qty
            cost_val += qty * cost
            retail_val += qty * sell
            
    return {
        "category_stock": [{"_id": k, "sku_count": v["sku_count"], "total_batches": v["total_batches"]} for k, v in cat_stock.items()],
        "prescription_ratio": [{"_id": k, "count": v} for k, v in rx_count.items()],
        "total_valuation": {
            "total_cost_value": round(cost_val, 2),
            "total_retail_value": round(retail_val, 2),
            "total_units": total_units
        }
    }
