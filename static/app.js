
let transactions=[],dashboardData=null;
const money=v=>"₹"+Number(v||0).toLocaleString("en-IN",{maximumFractionDigits:0});
async function api(url,opts={}){const r=await fetch(url,opts);const d=await r.json();if(!r.ok)throw new Error(d.detail||"Request failed");return d}
function showPage(name){
 document.querySelectorAll(".page").forEach(p=>p.classList.add("hidden"));
 const page=document.getElementById("page-"+name);if(page)page.classList.remove("hidden");
 document.querySelectorAll(".nav-link").forEach(b=>b.classList.toggle("active",b.dataset.page===name));
 history.replaceState(null,"","#"+name);
 if(name==="transactions")renderTransactions();
 if(name==="analytics"||name==="dashboard")drawCharts();
 window.scrollTo({top:0,behavior:"smooth"});
}
function badge(level){return `<span class="risk ${level}">${level}</span>`}
function recentRow(t){return `<tr><td><b>${t.transaction_id}</b></td><td>${t.customer_id}</td><td>${money(t.amount)}</td><td>${t.city}</td><td>${t.risk_score}/100</td><td>${badge(t.risk_level)}</td><td>${t.decision}</td></tr>`}
function renderTransactions(){
 const q=(document.getElementById("search")?.value||"").toLowerCase(),level=document.getElementById("riskFilter")?.value||"";
 const rows=transactions.filter(t=>(!level||t.risk_level===level)&&[t.transaction_id,t.customer_id,t.city].join(" ").toLowerCase().includes(q));
 const el=document.getElementById("allRows");if(!el)return;
 el.innerHTML=rows.length?rows.map(t=>`<tr><td>${t.transaction_id}</td><td>${t.customer_id}</td><td>${money(t.amount)}</td><td>${t.city}</td><td>${t.risk_score}/100</td><td>${badge(t.risk_level)}</td><td>${(t.reasons||[]).join("; ")}</td></tr>`).join(""):`<tr><td colspan="7" class="empty">No matching transactions.</td></tr>`;
}
function drawBarChart(canvasId,labels,values,colors){
 const c=document.getElementById(canvasId);if(!c)return;
 const ctx=c.getContext("2d"),w=c.clientWidth||500,h=c.clientHeight||240,dpr=window.devicePixelRatio||1;
 c.width=w*dpr;c.height=h*dpr;ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
 const pad={l:34,r:15,t:18,b:36},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b,max=Math.max(1,...values);
 ctx.strokeStyle="#2a3954";ctx.lineWidth=1;
 for(let i=0;i<4;i++){let y=pad.t+ch*i/3;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke()}
 const gap=cw/labels.length,bw=Math.min(62,gap*.48);
 values.forEach((v,i)=>{let bh=(v/max)*(ch-8),x=pad.l+gap*i+(gap-bw)/2,y=pad.t+ch-bh;ctx.fillStyle=colors[i];ctx.beginPath();ctx.roundRect(x,y,bw,bh,6);ctx.fill();ctx.fillStyle="#aab8d0";ctx.font="10px DM Sans";ctx.textAlign="center";ctx.fillText(String(v),x+bw/2,y-7);ctx.fillText(labels[i],x+bw/2,h-11)});
}
function drawScoreChart(){
 const c=document.getElementById("scoreChart");if(!c)return;
 const ctx=c.getContext("2d"),w=c.clientWidth||500,h=c.clientHeight||260,dpr=window.devicePixelRatio||1;c.width=w*dpr;c.height=h*dpr;ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
 const vals=transactions.slice(0,12).reverse().map(x=>x.risk_score),pad=30,cw=w-2*pad,ch=h-55;
 ctx.strokeStyle="#2a3954";for(let i=0;i<5;i++){let y=15+ch*i/4;ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(w-pad,y);ctx.stroke()}
 if(!vals.length){ctx.fillStyle="#91a2bf";ctx.fillText("Upload transactions to see scores",pad, h/2);return}
 const pts=vals.map((v,i)=>({x:pad+(vals.length===1?cw/2:cw*i/(vals.length-1)),y:15+ch-(v/100)*ch}));
 ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.strokeStyle="#8295ff";ctx.lineWidth=2.5;ctx.stroke();
 pts.forEach(p=>{ctx.beginPath();ctx.arc(p.x,p.y,4,0,Math.PI*2);ctx.fillStyle="#3bd9b4";ctx.fill()});
 ctx.fillStyle="#91a2bf";ctx.font="10px DM Sans";ctx.fillText("0",8,15+ch);ctx.fillText("100",4,22);
}
function drawCharts(){
 if(!dashboardData)return;
 const vals=[dashboardData.high,dashboardData.medium,dashboardData.low];
 drawBarChart("riskChart",["HIGH","MEDIUM","LOW"],vals,["#ff667e","#f4bd5c","#3bd9b4"]);
 drawBarChart("analyticsChart",["HIGH","MEDIUM","LOW"],vals,["#ff667e","#f4bd5c","#3bd9b4"]);
 drawScoreChart();
}
async function refreshAll(){
 try{
  const d=await api("/api/dashboard");dashboardData=d;
  document.getElementById("total").textContent=d.total;
  document.getElementById("high").textContent=d.high;
  document.getElementById("medium").textContent=d.medium;
  document.getElementById("runCount").textContent=d.runs.length;
  document.getElementById("recentRows").innerHTML=d.transactions.length?d.transactions.slice(0,8).map(recentRow).join(""):`<tr><td colspan="7" class="empty">No transactions yet. Run the pipeline.</td></tr>`;
  const runMarkup=d.runs.length?d.runs.map(r=>`<tr><td>${r.batch_id}</td><td>${r.source}</td><td>${r.input_rows}</td><td>${r.valid_rows}</td><td>${r.rejected_rows}</td><td>${r.duplicates}</td><td>${r.flagged}</td><td>${badge(r.status==="SUCCESS"?"LOW":"HIGH")}</td></tr>`).join(""):`<tr><td colspan="8" class="empty">No pipeline runs yet.</td></tr>`;
  ["pipelineRows","automationRows"].forEach(id=>{const el=document.getElementById(id);if(el)el.innerHTML=runMarkup});
  const latest=d.runs[0],sum=document.getElementById("pipelineSummary");
  if(sum)sum.innerHTML=latest?`<div class="summary-item"><b>${latest.status} · ${latest.batch_id}</b><small>Source: ${latest.source}</small></div><div class="summary-item"><b>${latest.valid_rows} valid / ${latest.input_rows} input records</b><small>${latest.rejected_rows} rejected · ${latest.duplicates} duplicates · ${latest.flagged} risk-flagged</small></div>`:`<div class="empty">No pipeline runs yet. Upload a CSV in Data pipeline.</div>`;
  transactions=await api("/api/transactions");renderTransactions();drawCharts();
 }catch(e){console.error("Dashboard refresh:",e)}
}
async function uploadCsv(){
 const f=document.getElementById("file").files[0],msg=document.getElementById("uploadMessage");
 if(!f){msg.textContent="Please choose a CSV file first.";return}
 const fd=new FormData();fd.append("file",f);msg.textContent="Pipeline running: Bronze → Silver → Gold…";
 try{const d=await api("/api/upload",{method:"POST",body:fd});msg.textContent=`${d.status} · Batch ${d.batch_id}: ${d.input_rows} input, ${d.valid_rows} valid, ${d.rejected_rows} rejected, ${d.duplicates} duplicates, ${d.flagged} flagged.`;await refreshAll()}
 catch(e){msg.textContent="Pipeline error: "+e.message}
}
window.addEventListener("resize",()=>drawCharts());
const initial=location.hash.replace("#","");showPage(["dashboard","pipeline","automation","transactions","analytics"].includes(initial)?initial:"home");
refreshAll();setInterval(refreshAll,10000);
