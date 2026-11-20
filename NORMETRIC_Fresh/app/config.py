import os
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
DATA=Path(os.getenv("NORMETRIC_DATA_DIR", BASE/"data"))
BRONZE,SILVER,GOLD,UPLOAD=[DATA/x for x in ("bronze","silver","gold","uploads")]
for p in (DATA,BRONZE,SILVER,GOLD,UPLOAD): p.mkdir(parents=True,exist_ok=True)
DB=DATA/"normetric.db"
