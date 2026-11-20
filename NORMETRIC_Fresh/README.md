# NORMETRIC — Data Engineering-Driven Fraud Monitoring

## What it demonstrates
- Bronze: preserve original uploaded CSV.
- Silver: required-field validation, type conversion, invalid-row rejection, duplicate removal.
- Gold: behavioral indicators, Isolation Forest support signal, risk score and explanation.
- Pipeline observability: batch ID, input/valid/rejected/duplicate/flagged counts and run history.
- Dark dashboard with 10-second refresh, CSV upload, search, risk distribution and export.

## Stack
Python, FastAPI, Pandas, scikit-learn Isolation Forest, SQLite, HTML/CSS/JavaScript, Render.

The local Bronze/Silver/Gold folders are CSV-based lakehouse-inspired layers, not actual Delta Lake tables. Spark and Databricks are not claimed as implemented. No paid cluster or GPU is required.

## Run on Windows
From the folder containing requirements.txt:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 and health check http://127.0.0.1:8000/health.

## Demo
1. Open Data pipeline and download/select static/sample_transactions.csv.
2. Click Run pipeline & score.
3. Show counts for valid, rejected and duplicate records.
4. Explain the Bronze, Silver and Gold CSV outputs under data/.
5. Inspect the risk distribution, run history and transaction explorer.
6. Export scored records.

The sample intentionally includes an invalid zero-amount row and a duplicate transaction ID.

## CSV
Required: transaction_id, customer_id, amount, city.
Optional: timestamp. Maximum upload: 5 MB.

## Deploy to Render
Push this folder to GitHub. In Render choose New > Blueprint and connect the repository. Review render.yaml, deploy, then test the generated URL and /health endpoint. The config mounts persistent storage at /var/data for SQLite and layer files. Confirm current hosting plan and disk pricing before deploying.

## Limitations
Scores are explainable risk indicators, not calibrated fraud probabilities. Decisions are simulated. Sample data is synthetic. Customer baselines are calculated within each uploaded batch for this educational demonstration. It is not connected to a payment network or production bank data.
