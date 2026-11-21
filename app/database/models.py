
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text
)
from sqlalchemy.sql import func

from .connection import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    batch_id = Column(String(30), primary_key=True)
    source = Column(String(255), nullable=False)
    input_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    flagged = Column(Integer, default=0)
    status = Column(String(30), default="PENDING")
    ran_at = Column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(100), primary_key=True)
    customer_id = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    city = Column(String(150), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="LOW")
    reasons = Column(Text)
    decision = Column(String(50))
    batch_id = Column(
        String(30),
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
