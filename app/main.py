import csv,io,json
from pathlib import Path
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.responses import HTMLResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from .config import BASE,UPLOAD
from .db import init,connect
from .etl import run_pipeline
app=FastAPI(title="NORMETRIC",version="1.0.0")
app.mount("/static",StaticFiles(directory=str(BASE/"static")),name="static")
@app.on_event("startup")
def startup(): init()
@app.get("/",response_class=HTMLResponse)
def home(): return (BASE/"static"/"index.html").read_text(encoding="utf-8")
@app.get("/health")
def health(): return {"status":"healthy","service":"NORMETRIC"}
@app.get("/api/dashboard")
def dashboard():
    with connect() as c:
        counts={x:c.execute("SELECT count(*) FROM transactions WHERE risk_level=?",(x,)).fetchone()[0] for x in ["HIGH","MEDIUM","LOW"]}
        total=c.execute("SELECT count(*) FROM transactions").fetchone()[0]
        rows=[dict(x) for x in c.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 15")]
        runs=[dict(x) for x in c.execute("SELECT * FROM runs ORDER BY ran_at DESC LIMIT 8")]
    for x in rows: x["reasons"]=json.loads(x["reasons"])
    return {"total":total,**{k.lower():v for k,v in counts.items()},"transactions":rows,"runs":runs}
@app.get("/api/transactions")
def transactions():
    with connect() as c: rows=[dict(x) for x in c.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 500")]
    for x in rows: x["reasons"]=json.loads(x["reasons"])
    return rows
@app.post("/api/upload")
async def upload(file:UploadFile=File(...)):
    if not file.filename.lower().endswith(".csv"): raise HTTPException(400,"Upload a CSV file.")
    data=await file.read()
    if len(data)>5*1024*1024: raise HTTPException(400,"Maximum upload size is 5 MB.")
    path=UPLOAD/(Path(file.filename).name)
    path.write_bytes(data)
    try: return run_pipeline(path,file.filename)
    except Exception as e: raise HTTPException(400,str(e))
@app.get("/api/export")
def export():
    with connect() as c: rows=c.execute("SELECT * FROM transactions ORDER BY created_at DESC").fetchall()
    s=io.StringIO(); w=csv.writer(s); w.writerow(rows[0].keys() if rows else ["transaction_id","customer_id","amount","city","timestamp","risk_score","risk_level","reasons","decision","batch_id","created_at"])
    for r in rows: w.writerow(list(r))
    return StreamingResponse(iter([s.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=normetric_results.csv"})
