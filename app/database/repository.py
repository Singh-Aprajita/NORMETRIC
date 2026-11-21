
import json
from datetime import datetime

from .connection import SessionLocal
from .models import Transaction, PipelineRun


def save_pipeline_results(batch, source, input_rows,
                          valid_rows, rejected_rows,
                          duplicates, flagged, rows):

    session = SessionLocal()

    try:
        # Save pipeline execution details
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

        session.merge(run)

        # Save processed transactions
        for row in rows:
            timestamp = None

            if row[4]:
                timestamp = datetime.fromisoformat(
                    row[4].replace("Z", "+00:00")
                )

            transaction = Transaction(
                transaction_id=row[0],
                customer_id=row[1],
                amount=row[2],
                city=row[3],
                timestamp=timestamp,
                risk_score=row[5],
                risk_level=row[6],
                reasons=row[7],
                decision=row[8],
                batch_id=row[9]
            )

            # Preserve the existing transaction-ID update behaviour
            session.merge(transaction)

        session.commit()
        return True

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()
