import sqlite3
from .config import DB
def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS transactions(
        transaction_id TEXT PRIMARY KEY, customer_id TEXT, amount REAL, city TEXT,
        timestamp TEXT, risk_score INTEGER, risk_level TEXT, reasons TEXT,
        decision TEXT, batch_id TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS runs(
        batch_id TEXT PRIMARY KEY, source TEXT, input_rows INTEGER, valid_rows INTEGER,
        rejected_rows INTEGER, duplicates INTEGER, flagged INTEGER, status TEXT, ran_at TEXT)""")
