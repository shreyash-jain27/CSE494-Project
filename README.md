# 💊 PharmaTrack: Intelligent NoSQL Medicine Expiry & Inventory System
### CSE494 Intelligent NoSQL Databases - Academic Task 2 (Project)

[![Python 3.11](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-MongoDB%207.0+-green.svg)](https://www.mongodb.com/)
[![Driver](https://img.shields.io/badge/Driver-PyMongo%204.0+-brightgreen.svg)](https://pymongo.readthedocs.io/)
[![Interface](https://img.shields.io/badge/UI-Streamlit%20%2B%20CLI-orange.svg)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/Tests-16%20Passed-success.svg)](https://pytest.org/)

---

## 📌 Project Overview
**PharmaTrack** is an end-to-end, production-grade document database application designed for pharmacies and medical inventory management. It solves critical real-world healthcare challenges:
- **Preventing the sale of expired drugs** through automated near-expiry alert pipelines.
- **Eliminating critical stockouts** with dynamic safety reorder thresholds.
- **Enforcing database-level data integrity** via native MongoDB JSON Schema validation (`$jsonSchema`).
- **Providing high-performance analytics** with multi-stage aggregation pipelines (`$unwind`, `$match`, `$group`, `$facet`, `$lookup`).

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated System Verification
Run the one-click verification script to test connection, schema validation, CRUD operations, and all 5 aggregation pipelines:
```bash
python verify_project.py
```

### 3. Launch the Modern React-Style Web App (Recommended)
For your presentation and live demonstration:
```bash
python web_app.py
```
*Opens an ultra-sleek, modern React-style Single Page Dashboard at `http://127.0.0.1:5000` with animated KPI cards, glassmorphism design, Lucide icons, Chart.js visual charts, interactive Point-of-Sale dispensing, and raw MongoDB query inspection.*

### 4. Alternative Interfaces
- **Streamlit Dashboard:**
  ```bash
  python -m streamlit run app.py
  ```
- **Terminal Console (CLI):**
  ```bash
  python cli.py
  ```

### 5. Run the Test Suite
```bash
python -m pytest tests/ -p no:cacheprovider -v
```
*(All 16 unit tests will run and pass).*

---

## 📂 Project Structure

```
CA-2 Project/
├── config/
│   ├── __init__.py
│   └── db_config.py            # MongoDB connection URI and client management
├── database/
│   ├── __init__.py
│   ├── schema_validation.py    # Native MongoDB $jsonSchema validators
│   └── seed_data.py            # Realistic pharmacy sample dataset seeder
├── core/
│   ├── __init__.py
│   ├── crud.py                 # Pure PyMongo CRUD business operations
│   └── aggregations.py         # 5 Multi-stage aggregation pipelines
├── tests/
│   ├── test_config.py          # Database connection tests
│   ├── test_schema_validation.py # $jsonSchema validation tests
│   ├── test_seed_data.py       # Dataset seeder verification
│   ├── test_crud.py            # Complete CRUD unit tests
│   ├── test_aggregations.py    # Aggregation pipelines unit tests
│   └── test_cli.py             # CLI formatting and negative test suite
├── docs/
│   ├── CSE494_CA2_Project_Report.md  # Complete academic report (CO4, CO5, CO6)
│   ├── VIVA_CHEAT_SHEET.md     # Top 15 examiner questions & live query modifications
│   └── superpowers/            # Architecture specs and implementation plans
├── app.py                      # Modern Streamlit interactive web dashboard
├── cli.py                      # Interactive terminal menu application for viva
├── cli_app.py                  # Core terminal formatting and dispatcher
├── verify_project.py           # Automated end-to-end verification suite
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable configuration template
└── README.md                   # This project guide
```

---

## 🔑 Key MongoDB Concepts Implemented

### 1. Document Structure & Schema Design
- **`medicines` Collection (Embedded Batches):** Stores drug details and an embedded array of active batches (`batch_no`, `expiry_date`, `quantity`, `selling_price`).  
  *Viva rationale:* 1-to-few relationship; accessed together during dispensing; enables single-read $O(1)$ lookups without multi-table joins.
- **`sales` Collection (Referenced Design):** Stores customer transaction invoices referencing `medicine_id`.  
  *Viva rationale:* 1-to-millions relationship; prevents exceeding MongoDB's 16MB document limit.

### 2. MongoDB Schema Validation (`$jsonSchema`)
Enforced at the collection level to block:
- Negative stock quantities (`minimum: 0`)
- Negative or zero selling prices (`minimum: 0.01`)
- Invalid therapeutic categories (enforced via `enum` list)
- Invoices without items (`minItems: 1`)

### 3. Multi-Stage Aggregation Pipelines
1. **Near-Expiry Batch Alerts:** `$unwind` $\rightarrow$ `$match` ($quantity > 0$ and $expiry \le date$) $\rightarrow$ `$project` (computes financial value at risk) $\rightarrow$ `$sort` by date.
2. **Low-Stock Reorder Thresholds:** `$project` (computes $total\_stock$ via `$sum` on batches) $\rightarrow$ `$match` ($total\_stock \le min\_reorder\_level$) $\rightarrow$ `$sort`.
3. **Category Revenue Breakdown:** `$unwind` items $\rightarrow$ `$lookup` from medicines $\rightarrow$ `$unwind` $\rightarrow$ `$group` by category $\rightarrow$ `$sort`.
4. **Top 5 Bestsellers:** `$unwind` items $\rightarrow$ `$group` by medicine $\rightarrow$ `$sort` by volume $\rightarrow$ `$limit`.
5. **Multi-Faceted Dashboard:** `$facet` returning SKU counts, prescription ratios, and total inventory procurement vs retail valuation in a single database call.

---

## 🎓 Academic Viva & Presentation Readiness
- Check [docs/CSE494_CA2_Project_Report.md](docs/CSE494_CA2_Project_Report.md) for the complete academic report formatted for submission.
- Check [docs/VIVA_CHEAT_SHEET.md](docs/VIVA_CHEAT_SHEET.md) for pre-answered viva questions and live query modification examples.
