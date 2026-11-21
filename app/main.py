
import csv
import io
import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE, UPLOAD
from .db import init
from .etl import run_pipeline
from .database.repository import (
    get_dashboard_data,
    get_transactions
)
from .database.connection import SessionLocal
from .database.models import Transaction


app = FastAPI(title="NORMETRIC", version="1.1.0")

app.mount(
    "/static",
    StaticFiles(directory=str(BASE / "static")),
    name="static"
)


# -------------------------------
# Application startup
# -------------------------------

@app.on_event("startup")
def startup():
    # Preserve existing SQLite initialization
    init()


# -------------------------------
# Home page
# -------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return (
        BASE / "static" / "index.html"
    ).read_text(encoding="utf-8")


# -------------------------------
# Health check
# -------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "NORMETRIC"
    }


# -------------------------------
# Dashboard - PostgreSQL
# -------------------------------

@app.get("/api/dashboard")
def dashboard():

    data = get_dashboard_data()

    # Convert stored JSON reasons into Python lists
    for transaction in data["transactions"]:
        transaction["reasons"] = json.loads(
            transaction["reasons"] or "[]"
        )

    return data


# -------------------------------
# Transaction explorer - PostgreSQL
# -------------------------------

@app.get("/api/transactions")
def transactions():

    rows = get_transactions()

    for transaction in rows:
        transaction["reasons"] = json.loads(
            transaction["reasons"] or "[]"
        )

    return rows


# -------------------------------
# CSV upload
# -------------------------------

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            400,
            "Upload a CSV file."
        )

    data = await file.read()

    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(
            400,
            "Maximum upload size is 5 MB."
        )

    path = UPLOAD / Path(file.filename).name
    path.write_bytes(data)

    try:
        return run_pipeline(path, file.filename)

    except Exception as error:
        raise HTTPException(
            400,
            str(error)
        )


# -------------------------------
# CSV export - PostgreSQL
# -------------------------------

@app.get("/api/export")
def export():

    session = SessionLocal()

    try:
        rows = (
            session.query(Transaction)
            .order_by(Transaction.created_at.desc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)

        columns = [
            "transaction_id",
            "customer_id",
            "amount",
            "city",
            "timestamp",
            "risk_score",
            "risk_level",
            "reasons",
            "decision",
            "batch_id",
            "created_at"
        ]

        writer.writerow(columns)

        for transaction in rows:
            writer.writerow([
                transaction.transaction_id,
                transaction.customer_id,
                transaction.amount,
                transaction.city,
                transaction.timestamp,
                transaction.risk_score,
                transaction.risk_level,
                transaction.reasons,
                transaction.decision,
                transaction.batch_id,
                transaction.created_at
            ])

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=normetric_results.csv"
            }
        )

    finally:
        session.close()
