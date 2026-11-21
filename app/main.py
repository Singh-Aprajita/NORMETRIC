
import csv
import io
import json
import traceback
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import BASE, UPLOAD
from .db import init
from .etl import run_pipeline
from .database.repository import (
    get_dashboard_data,
    get_transactions
)
from .database.connection import SessionLocal
from .database.models import Transaction
from .ai_service import explain_transaction, answer_assistant


# --------------------------------
# Application configuration
# --------------------------------

app = FastAPI(title="NORMETRIC", version="1.3.1")

app.mount(
    "/static",
    StaticFiles(directory=str(BASE / "static")),
    name="static"
)


# --------------------------------
# AI assistant request model
# --------------------------------

class AssistantRequest(BaseModel):
    question: str
    history: list[dict] = Field(default_factory=list)


# --------------------------------
# Startup
# --------------------------------

@app.on_event("startup")
def startup():
    init()


# --------------------------------
# Home and health
# --------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return (
        BASE / "static" / "index.html"
    ).read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "NORMETRIC"
    }


# --------------------------------
# Dashboard API
# --------------------------------

@app.get("/api/dashboard")
def dashboard():
    data = get_dashboard_data()

    for transaction in data.get("transactions", []):
        reasons = transaction.get("reasons") or "[]"

        if isinstance(reasons, str):
            transaction["reasons"] = json.loads(reasons)

    return data


# --------------------------------
# Transactions API
# --------------------------------

@app.get("/api/transactions")
def transactions():
    rows = get_transactions()

    for transaction in rows:
        reasons = transaction.get("reasons") or "[]"

        if isinstance(reasons, str):
            transaction["reasons"] = json.loads(reasons)

    return rows


# --------------------------------
# AI transaction explanation
# --------------------------------

@app.post("/api/ai/explain/{transaction_id}")
def ai_explain(transaction_id: str):

    session = SessionLocal()

    try:
        transaction = (
            session.query(Transaction)
            .filter_by(transaction_id=transaction_id)
            .first()
        )

        if not transaction:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found"
            )

        transaction_data = {
            "amount": transaction.amount,
            "risk_score": transaction.risk_score,
            "risk_level": transaction.risk_level,
            "reasons": json.loads(
                transaction.reasons or "[]"
            )
        }

    finally:
        session.close()

    try:
        explanation = explain_transaction(transaction_data)

        return {
            "transaction_id": transaction_id,
            "explanation": explanation
        }

    except Exception as error:
        print("\n--- AI EXPLANATION ERROR ---")
        traceback.print_exc()

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )


# --------------------------------
# NORMETRIC conversational AI assistant
# --------------------------------

@app.post("/api/ai/chat")
def ai_chat(request: AssistantRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question."
        )

    if len(question) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Question is too long."
        )

    try:
        # Fetch current database information
        dashboard_data = get_dashboard_data()
        transactions_data = get_transactions()

        # Identify transaction IDs mentioned in the question
        matched = [
            t for t in transactions_data
            if str(t.get("transaction_id", "")).lower()
            in question.lower()
        ]

        # Select highest-risk transactions
        high_risk = sorted(
            [
                t for t in transactions_data
                if t.get("risk_level") == "HIGH"
            ],
            key=lambda x: float(x.get("risk_score") or 0),
            reverse=True
        )[:5]

        # Prepare transaction data for AI
        def prepare_transaction(transaction):
            reasons = transaction.get("reasons") or []

            if isinstance(reasons, str):
                try:
                    reasons = json.loads(reasons)
                except (json.JSONDecodeError, TypeError):
                    reasons = [reasons]

            return {
                "transaction_id": transaction.get("transaction_id"),
                "amount": transaction.get("amount"),
                "city": transaction.get("city"),
                "risk_score": transaction.get("risk_score"),
                "risk_level": transaction.get("risk_level"),
                "reasons": reasons,
                "decision": transaction.get("decision")
            }

        # Build read-only database context
        context = {
            "total_transactions": dashboard_data.get("total", 0),
            "high_risk_count": dashboard_data.get("high", 0),
            "medium_risk_count": dashboard_data.get("medium", 0),
            "low_risk_count": dashboard_data.get("low", 0),

            "highest_risk_transactions": [
                prepare_transaction(t)
                for t in high_risk
            ],

            "recent_transactions": [
                prepare_transaction(t)
                for t in transactions_data[:5]
            ],

            "matched_transactions": [
                prepare_transaction(t)
                for t in matched[:5]
            ],

            "recent_pipeline_runs": dashboard_data.get(
                "runs", []
            )[:5]
        }

        # Generate AI response
        answer = answer_assistant(
            question,
            context,
            request.history
        )

        return {
            "answer": answer
        }

    except Exception as error:
        print("\n--- NORMETRIC AI ASSISTANT ERROR ---")
        traceback.print_exc()

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )


# --------------------------------
# CSV upload and ETL execution
# --------------------------------

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Upload a CSV file."
        )

    data = await file.read()

    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Maximum upload size is 5 MB."
        )

    path = UPLOAD / Path(file.filename).name
    path.write_bytes(data)

    try:
        return run_pipeline(path, file.filename)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# --------------------------------
# Export transaction records
# --------------------------------

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
