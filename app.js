const DATA_URL = "data/stocks.json";
const money = n => n == null ? "—" : new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(n);
const capFmt = n => n == null ? "—" : n >= 1e9 ? `$${(n/1e9).toFixed(2)}B` : `$${(n/1e6).toFixed(1)}M`;
const pctFmt = n => `${n > 0 ? "+" : ""}${Number(n).toFixed(2)}%`;
const esc = s => String(s ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let stocks = [];

function sparkline(values){
  if(!values || !values.length) return '<span class="muted-small">No MACD data</span>';
  const w=150,h=35,mid=17.5,max=Math.max(...values.map(v=>Math.abs(v)),0.000001);
  const gap=4,bw=(w-gap*(values.length-1))/values.length;
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" role="img" aria-label="Five-day MACD histogram">${values.map((v,i)=>{const bh=Math.max(2,Math.abs(v)/max*14);const x=i*(bw+gap);const y=v>=0?mid-bh:mid;return `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="2" fill="${v>=0?'#2bd6a0':'#ff657a'}"/>`}).join("")}<line x1="0" y1="${mid}" x2="${w}" y2="${mid}" stroke="#64758e" stroke-width=".8"/></svg>`;
}
function detailMarkup(s){
 const macd=s.macd||{};
 const highs=(s.highs||[]).map(x=>`<div class="extreme-item"><span>${esc(x.date)}</span><span>${money(x.price)}</span></div>`).join("")||'<span class="muted-small">Unavailable</span>';
 const lows=(s.lows||[]).map(x=>`<div class="extreme-item"><span>${esc(x.date)}</span><span>${money(x.price)}</span></div>`).join("")||'<span class="muted-small">Unavailable</span>';
 const hist=(macd.histogram||[]).map(x=>`<span>${esc(x.date)} <b class="${x.value>=0?'positive-text':'negative-text'}">${Number(x.value).toFixed(4)}</b></span>`).join("");
 return `<tr class="detail-row"><td colspan="7"><div class="details">
 <section><div class="detail-title">MACD / LAST 5 SESSIONS</div><div class="macd-values"><span>MACD <b>${macd.macd==null?'—':Number(macd.macd).toFixed(4)}</b></span><span>Signal <b>${macd.signal==null?'—':Number(macd.signal).toFixed(4)}</b></span><span>Histogram <b>${macd.latest_histogram==null?'—':Number(macd.latest_histogram).toFixed(4)}</b></span></div><div class="macd-values" style="margin-top:10px">${hist}</div></section>
 <section><div class="detail-title">TOP 3 52-WEEK HIGH DAYS</div><div class="extreme-list">${highs}</div></section>
 <section><div class="detail-title">TOP 3 52-WEEK LOW DAYS</div><div class="extreme-list">${lows}</div></section>
 </div></td></tr>`;
}
function render(){
 const q=document.getElementById("search").value.trim().toLowerCase();
 const visible=stocks.filter(s=>(s.ticker+" "+s.name).toLowerCase().includes(q));
 const body=document.getElementById("stock-rows");
 body.innerHTML=visible.map((s,i)=>`<tr class="stock-row" data-ticker="${esc(s.ticker)}">
 <td>${i+1}</td><td><a class="ticker" href="https://www.tradingview.com/chart/?symbol=${encodeURIComponent(s.ticker)}" target="_blank" rel="noopener">${esc(s.ticker)}</a><div class="company">${esc(s.name)}</div></td>
 <td class="price">${money(s.close)}</td><td class="right negative">${pctFmt(s.change_pct)}</td><td class="cap">${capFmt(s.market_cap)}</td><td>${sparkline(s.macd?.histogram?.map(x=>x.value)||[])}</td><td><button class="expand-btn" aria-expanded="false">Details +</button></td></tr>`).join("");
 document.getElementById("empty").hidden=visible.length!==0;
 body.querySelectorAll(".expand-btn").forEach(btn=>btn.addEventListener("click",()=>{
   const row=btn.closest("tr"),ticker=row.dataset.ticker,open=btn.getAttribute("aria-expanded")==="true";
   const next=row.nextElementSibling;
   if(open){if(next?.classList.contains("detail-row"))next.remove();btn.textContent="Details +";btn.setAttribute("aria-expanded","false");}
   else{const s=stocks.find(x=>x.ticker===ticker);row.insertAdjacentHTML("afterend",detailMarkup(s));btn.textContent="Close −";btn.setAttribute("aria-expanded","true");}
 }));
}
async function load(){
 try{
  const response=await fetch(DATA_URL+"?v="+Date.now(),{cache:"no-store"});
  if(!response.ok)throw new Error(`Could not load data (${response.status}).`);
  const data=await response.json();stocks=data.stocks||[];
  document.getElementById("session-date").textContent=data.session_date||"Not available";
  document.getElementById("updated-at").textContent=data.updated_at?`Updated ${data.updated_at} · ${data.provider||"Market data"}`:"No update timestamp";
  document.getElementById("match-count").textContent=stocks.length;
  const note=data.note|| (stocks.length?"Showing qualifying stocks from the latest completed trading session.":"No qualifying stocks were found.");
  document.getElementById("notice").textContent=note;
  if(data.error){document.getElementById("notice").classList.add("error");}
  render();
 }catch(e){document.getElementById("notice").textContent=e.message+" The first daily scan may not have run yet.";document.getElementById("notice").classList.add("error");}
}
document.getElementById("search").addEventListener("input",render);
load();
