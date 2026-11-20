from pathlib import Path
import pandas as pd
from app.etl import REQ
p=Path('static/sample_transactions.csv')
d=pd.read_csv(p)
assert set(REQ).issubset(d.columns)
assert len(d)==17
print('Preflight passed: sample CSV schema and 17 rows verified.')
