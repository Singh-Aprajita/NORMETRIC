
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from .connection import SessionLocal
from .models import Transaction, PipelineRun


# --------------------------------
# Save ETL results to PostgreSQL
# --------------------------------

def save_pipeline_results(
    batch,
    source,
    input_rows,
    valid_rows,
    rejected_rows,
    duplicates,
    flagged,
    rows
):
    session = SessionLocal()

    try:
        # Record every pipeline execution
        run = PipelineRun(
            batch_id=batch,
            source=source,
            input_rows=input_rows,
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
            duplicates=duplicates,
            flagged=flagged,
            status="SUCCESS"
        )

        session.add(run)

        # Prepare transaction records
        records = []

        for row in rows:
            timestamp = None

            if row[4]:
                timestamp = datetime.fromisoformat(
                    row[4].replace("Z", "+00:00")
                )

            records.append({
                "transaction_id": row[0],
                "customer_id": row[1],
                "amount": row[2],
                "city": row[3],
                "timestamp": timestamp,
                "risk_score": row[5],
                "risk_level": row[6],
                "reasons": row[7],
                "decision": row[8],
                "batch_id": row[9]
            })

        # Insert only new transaction IDs.
        # Existing records will not be overwritten.
        if records:
            statement = insert(Transaction).values(records)

            statement = statement.on_conflict_do_nothing(
                index_elements=["transaction_id"]
            )

            session.execute(statement)

        session.commit()
        return True

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


# --------------------------------
# Dashboard data
# --------------------------------

def get_dashboard_data():
    session = SessionLocal()

    try:
        counts = {
            level: session.query(
                func.count(Transaction.transaction_id)
            ).filter(
                Transaction.risk_level == level
            ).scalar()
            for level in ["HIGH", "MEDIUM", "LOW"]
        }

        total = session.query(
            func.count(Transaction.transaction_id)
        ).scalar()

        transactions = (
            session.query(Transaction)
            .order_by(Transaction.created_at.desc())
            .limit(15)
            .all()
        )

        runs = (
            session.query(PipelineRun)
            .order_by(PipelineRun.ran_at.desc())
            .limit(8)
            .all()
        )

        return {
            "total": total,
            "high": counts["HIGH"],
            "medium": counts["MEDIUM"],
            "low": counts["LOW"],

            "transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "customer_id": t.customer_id,
                    "amount": t.amount,
                    "city": t.city,
                    "timestamp": t.timestamp,
                    "risk_score": t.risk_score,
                    "risk_level": t.risk_level,
                    "reasons": t.reasons,
                    "decision": t.decision,
                    "batch_id": t.batch_id,
                    "created_at": t.created_at,
                }
                for t in transactions
            ],

            "runs": [
                {
                    "batch_id": r.batch_id,
                    "source": r.source,
                    "input_rows": r.input_rows,
                    "valid_rows": r.valid_rows,
                    "rejected_rows": r.rejected_rows,
                    "duplicates": r.duplicates,
                    "flagged": r.flagged,
                    "status": r.status,
                    "ran_at": r.ran_at,
                }
                for r in runs
            ],
        }

    finally:
        session.close()


# --------------------------------
# Transaction explorer
# --------------------------------

def get_transactions():
    session = SessionLocal()

    try:
        transactions = (
            session.query(Transaction)
            .order_by(Transaction.created_at.desc())
            .limit(500)
            .all()
        )

        return [
            {
                "transaction_id": t.transaction_id,
                "customer_id": t.customer_id,
                "amount": t.amount,
                "city": t.city,
                "timestamp": t.timestamp,
                "risk_score": t.risk_score,
                "risk_level": t.risk_level,
                "reasons": t.reasons,
                "decision": t.decision,
                "batch_id": t.batch_id,
                "created_at": t.created_at,
            }
            for t in transactions
        ]

    finally:
        session.close()
