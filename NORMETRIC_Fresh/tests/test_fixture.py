from pathlib import Path
import pandas as pd

def test_sample_fixture_contains_required_columns():
    p=Path(__file__).parents[1]/"static"/"sample_transactions.csv"
    d=pd.read_csv(p)
    assert {"transaction_id","customer_id","amount","city"} <= set(d.columns)
    assert len(d)==17

def test_sample_fixture_has_invalid_and_duplicate_rows():
    d=pd.read_csv(Path(__file__).parents[1]/"static"/"sample_transactions.csv")
    assert (pd.to_numeric(d.amount,errors="coerce")<=0).any()
    assert d.transaction_id.duplicated().any()
