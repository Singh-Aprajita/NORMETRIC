import json, uuid
from datetime import datetime, timezone
import pandas as pd
from sklearn.ensemble import IsolationForest
from .config import BRONZE,SILVER,GOLD
from .db import connect
REQ=["transaction_id","customer_id","amount","city"]
def stamp(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def run_pipeline(path, source):
    batch="B-"+uuid.uuid4().hex[:9].upper()
    raw=pd.read_csv(path); n=len(raw)
    raw.to_csv(BRONZE/f"{batch}.csv",index=False)
    missing=[x for x in REQ if x not in raw.columns]
    if missing: raise ValueError("Missing required columns: "+", ".join(missing))
    d=raw.copy()
    for col in ("transaction_id","customer_id","city"):
        d[col]=d[col].fillna("").astype(str).str.strip()
    d["amount"]=pd.to_numeric(d["amount"],errors="coerce")
    if "timestamp" not in d: d["timestamp"]=""
    d["timestamp"]=pd.to_datetime(d["timestamp"],errors="coerce",utc=True)
    valid=d.transaction_id.ne("") & d.customer_id.ne("") & d.city.ne("") & d.amount.notna() & d.amount.gt(0)
    rejected=int((~valid).sum()); d=d[valid].copy()
    before=len(d); d=d.drop_duplicates("transaction_id",keep="last"); dup=before-len(d)
    d.to_csv(SILVER/f"{batch}.csv",index=False)
    if "timestamp" not in d: d["timestamp"]=pd.NaT
    d["_hour"]=d.timestamp.dt.hour.fillna(12)
    d["_burst"]=1
    for ix,r in d.iterrows():
        if pd.notna(r.timestamp):
            same=d[(d.customer_id==r.customer_id)&d.timestamp.notna()]
            d.loc[ix,"_burst"]=int(((same.timestamp-r.timestamp).abs()<=pd.Timedelta(minutes=10)).sum())
    anomaly=set()
    if len(d)>=10:
        model=IsolationForest(contamination=.08,random_state=42)
        features=d[["amount","_hour","_burst"]].fillna(0)
        anomaly=set(d.index[model.fit_predict(features)==-1])
    avg=d.groupby("customer_id").amount.mean().to_dict()
    city_counts=d.groupby(["customer_id","city"]).size().reset_index(name="n")
    usual=city_counts.sort_values("n").drop_duplicates("customer_id",keep="last").set_index("customer_id").city.to_dict()
    out=[]
    for ix,r in d.iterrows():
        score=0; reasons=[]
        if r.amount>max(avg[r.customer_id]*3,avg[r.customer_id]+5000):
            score+=30; reasons.append("Amount is unusually high for this customer batch")
        if r.city!=usual.get(r.customer_id,r.city):
            score+=20; reasons.append("City differs from the customer's most-used city")
        if pd.notna(r.timestamp) and r.timestamp.hour<=4:
            score+=15; reasons.append("Transaction occurred between midnight and 4 AM")
        if r._burst>=4:
            score+=25; reasons.append(f"{int(r._burst)} transactions within a 10-minute window")
        if ix in anomaly:
            score+=15; reasons.append("Isolation Forest identified an unusual feature combination")
        score=min(100,score); level="HIGH" if score>=60 else "MEDIUM" if score>=30 else "LOW"
        decision="BLOCK (SIMULATED)" if level=="HIGH" else "REVIEW" if level=="MEDIUM" else "ALLOW (SIMULATED)"
        if not reasons: reasons=["No configured risk indicator triggered"]
        out.append((str(r.transaction_id),str(r.customer_id),float(r.amount),str(r.city),
                    "" if pd.isna(r.timestamp) else r.timestamp.isoformat(),score,level,
                    json.dumps(reasons),decision,batch,stamp()))
    pd.DataFrame(out,columns=["transaction_id","customer_id","amount","city","timestamp","risk_score","risk_level","reasons","decision","batch_id","created_at"]).to_csv(GOLD/f"{batch}.csv",index=False)
    flagged=sum(x[6]!="LOW" for x in out)
    with connect() as c:
        c.executemany("""INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(transaction_id) DO UPDATE SET customer_id=excluded.customer_id,amount=excluded.amount,
        city=excluded.city,timestamp=excluded.timestamp,risk_score=excluded.risk_score,
        risk_level=excluded.risk_level,reasons=excluded.reasons,decision=excluded.decision,
        batch_id=excluded.batch_id,created_at=excluded.created_at""",out)
        c.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)",(batch,source,n,len(out),rejected,dup,flagged,"SUCCESS",stamp()))
    return {"batch_id":batch,"input_rows":n,"valid_rows":len(out),"rejected_rows":rejected,"duplicates":dup,"flagged":flagged,"status":"SUCCESS"}
