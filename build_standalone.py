import json, pathlib, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from i18n_generated import LANGS, THEMES
from i18n import THEME_TRAD as _TZ_TRAD
from naming import is_generic
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from naming import is_generic
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent

CJK_OK = set("·　、。，！？「」『』（）：；～")


def _clean(raw: str) -> str:
    """Normalise display text without deleting meaning.

    The exports contain ▓ blocks and U+FFFC object-replacement characters where an image or
    a redacted username sat in the original post. We collapse runs of them into one visible
    marker so a reader knows something was there, rather than silently removing it and
    leaving a sentence that looks complete but is not.
    """
    txt = re.sub(r"[\u2580-\u259f\ufffc\ufffe\uf800-\uf8ff]+", "［圖片／已隱去］", raw)
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt.strip()


def prepare():
    """Recompute the embedded payload from the analysed parquet."""
    df = pd.read_parquet(ROOT / "data" / "analysed.parquet")
    stats = json.loads((ROOT / "data" / "stats.json").read_text())
    TZ = {"queue":"排隊輪候","cleanliness":"衛生環境","service_attitude":"服務態度","taste":"口味品質",
          "price":"價格性價比","portion":"分量","opening_hours":"營業時間/結業","delivery_delay":"外送延誤",
          "delivery_missing":"漏送缺品","staff_behaviour":"員工行為","menu_availability":"貨品供應","other":"其他"}
    dates = pd.to_datetime(df.date, errors="coerce")
    ref = dates.max()
    df = df.assign(days=((ref - dates).dt.days).clip(lower=0))

    live = df[df.relevant & (df.days <= 90)].copy()
    pool = live.sort_values("priority", ascending=False).head(500)
    rows = [dict(src=r.source, store=(r.store if isinstance(r.store,str) else ""),
                 date=str(r.date)[:10] if pd.notna(r.date) else "",
                 text=_clean(str(r.text))[:400],
                 themes=[TZ.get(t,t) for t in r.themes], senti=r.sentiment, crisis=bool(r.crisis),
                 pr=round(float(r.priority),1), days=int(r.days), conf=r.confidence,
                 url=r.url if isinstance(r.url,str) else "") for _, r in pool.iterrows()]

    # ---- the four numbers a communications manager actually works against
    neg_live = live[live.sentiment=="negative"]
    pos_live = live[live.sentiment=="positive"]
    backlog  = int((neg_live.days > 7).sum())
    by_src = {}
    for src, g in live[live.sentiment.isin(["negative","positive"])].groupby("source"):
        by_src[src] = dict(open=int(len(g)), med_days=int(g.days.median()),
                           avg_days=int(g.days.mean()),
                           neg=int((g.sentiment=="negative").sum()))
    hot = Counter(t for ts in neg_live.themes for t in ts if t!="other")

    # A listing whose name is only the chain title tells us nothing about which branch it is.
    df = df.assign(branch_named=~df.store.map(is_generic))
    named = df[df.lat.notna() & df.branch_named]
    g = (named.groupby(["store","lat","lng"])
         .agg(n=("text","size"), neg=("sentiment", lambda x: int((x=="negative").sum())),
              newest=("days","min")).reset_index())
    g["rate"] = (g.neg/g.n*100).round(1)
    branches = [dict(store=r.store, lat=float(r.lat), lng=float(r.lng), n=int(r.n),
                     neg=int(r.neg), rate=float(r.rate), newest=int(r.newest)) for _, r in g.iterrows()]

    neg_all = df[df.relevant & (df.sentiment=="negative")]
    written = neg_all[neg_all.text.str.strip().str.len()>=5]
    tc = Counter(t for ts in written.themes for t in ts if t!="other")
    themes = sorted(([TZ[k],v] for k,v in tc.items()), key=lambda x:-x[1])[:9]
    meas = df[df.latency_measurable & df.relevant & (df.sentiment=="negative")]
    return dict(stats=stats, rows=rows, branches=branches, themes=themes,
                unnamed_outlets=int(df.store.map(is_generic).sum()),
                located_branches=int(named.store.nunique()),
                silent_all=int((df.text.str.strip().str.len()<5).sum()),
                silent_negative=int((neg_all.text.str.strip().str.len()<5).sum()),
                pending_neg=len(neg_live), pending_pos=len(pos_live), backlog=backlog,
                crisis_live=int(live.crisis.sum()), by_src=by_src,
                hot=[[k,v] for k,v in hot.most_common(6)],   # keys, translated client-side
                oldest_days=int(neg_live.days.max()) if len(neg_live) else 0,
                oldest_platform=(neg_live.sort_values("days", ascending=False).iloc[0].source
                                 if len(neg_live) else "—"),
                hot_total=int(sum(hot.values())),
                buckets=[["b1", int((meas.days <= 7).sum())],
                         ["b2", int(((meas.days > 7) & (meas.days <= 30)).sum())],
                         ["b3", int(((meas.days > 30) & (meas.days <= 90)).sum())]],
                negatives=len(neg_all), written=len(written))


data = json.dumps(prepare(), ensure_ascii=False)
languages = json.dumps(LANGS, ensure_ascii=False)
themes = json.dumps(THEMES, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title id="pageTitle">譚仔 · 顧客回饋中心</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"PingFang HK","Microsoft YaHei",Arial,sans-serif;background:#F7F4EF;color:#1A1A1A;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto;padding:26px 20px 60px}
.hero{background:linear-gradient(135deg,#C8102E,#7A0C1B);color:#fff;padding:34px 30px;border-radius:16px;margin-bottom:22px}
.hero h1{font-size:30px;letter-spacing:-.6px;margin-bottom:9px}
.hero .lead{font-size:16.5px;font-weight:600;margin-bottom:6px}
.hero .sub{opacity:.88;font-size:14.5px;max-width:760px}
.tabs{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}
.tab{padding:9px 17px;border:1px solid #DDD6CC;background:#fff;border-radius:9px;cursor:pointer;font-size:14px;font-weight:600;color:#5A6272}
.tab.on{background:#C8102E;color:#fff;border-color:#C8102E}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:22px}
.kpi{background:#fff;border:1px solid #E7E2DA;border-radius:12px;padding:16px 18px}
.kpi b{display:block;font-size:27px;color:#C8102E;font-weight:700}
.kpi span{font-size:13px;color:#5A6272;display:block;margin-top:3px}
.card{background:#fff;border:1px solid #E7E2DA;border-radius:12px;padding:15px 17px;margin-bottom:11px}
.crisis{border-left:4px solid #C8102E;background:#FFF6F6}
.meta{display:flex;gap:14px;align-items:center;font-size:12.5px;color:#7A8494;flex-wrap:wrap;margin-bottom:8px}
.src{background:#EEF1F6;padding:3px 9px;border-radius:5px;font-weight:700;color:#2F3A4A;font-size:12px}
.badge{font-weight:700;font-size:12px;padding:3px 9px;border-radius:5px}
.b-neg{background:#FDECEA;color:#B0342A}.b-pos{background:#E8F5EC;color:#256D46}.b-neu{background:#EEF1F6;color:#5A6272}.b-crisis{background:#C8102E;color:#fff}
.body{font-size:14.5px;margin:7px 0 9px;word-break:break-word}
.tags span{display:inline-block;background:#F3EFE8;color:#6B5D4A;font-size:11.5px;padding:2px 8px;border-radius:4px;margin-right:5px}
.acts{display:flex;gap:7px;margin-top:11px;flex-wrap:wrap;align-items:center}
.btn{padding:6px 13px;border:1px solid #DDD6CC;background:#fff;border-radius:7px;cursor:pointer;font-size:12.5px;font-weight:600}
.btn:hover:not(:disabled){border-color:#C8102E;color:#C8102E}
.btn:disabled{opacity:.4;cursor:not-allowed;text-decoration:line-through}
.done{font-size:12px;color:#256D46;font-weight:700}
.filters{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
select,input[type=search]{padding:8px 11px;border:1px solid #DDD6CC;border-radius:8px;background:#fff;font-size:13.5px}
.chart{background:#fff;border:1px solid #E7E2DA;border-radius:12px;padding:18px;margin-bottom:16px}
.bar{display:grid;grid-template-columns:96px 1fr 52px;align-items:center;gap:11px;margin:9px 0;font-size:13px}
.track{background:#F3EFE8;border-radius:4px;height:21px;overflow:hidden}
.fill{height:100%;background:#2F6B45;border-radius:4px}
.note{background:#FFF8E7;border:1px solid #F0DFAE;border-radius:10px;padding:13px 15px;font-size:13px;color:#6B5A28;margin-bottom:16px}
.map{position:relative;height:520px;background:#fff;border:1px solid #E7E2DA;border-radius:12px;overflow:hidden}
.pt{position:absolute;border-radius:50%;transform:translate(-50%,-50%);cursor:pointer;border:1.5px solid rgba(0,0,0,.18)}
.pt:hover::after{content:attr(data-t);position:absolute;bottom:115%;left:50%;transform:translateX(-50%);background:#1A1A1A;color:#fff;padding:6px 9px;border-radius:6px;font-size:11.5px;white-space:nowrap;z-index:9}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:9px 8px;border-bottom:2px solid #E7E2DA;color:#5A6272;font-size:12px}
td{padding:9px 8px;border-bottom:1px solid #F1EDE6}
.hide{display:none}
.legend{display:flex;gap:16px;font-size:12px;color:#5A6272;margin-top:11px;align-items:center}
.dot{width:11px;height:11px;border-radius:50%;display:inline-block;margin-right:5px}
h2{font-size:19px;margin-bottom:13px}h3{font-size:15px;margin:18px 0 9px}
footer{margin-top:30px;font-size:12px;color:#8A94A6;line-height:1.7}
a{color:#C8102E}
.split{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}
@media(max-width:900px){.split{grid-template-columns:1fr}}
.kpi em{display:block;font-size:11.5px;color:#8A94A6;font-style:normal;margin-top:4px;line-height:1.4}
.cap{font-size:11.5px;color:#8A94A6;margin-top:12px;line-height:1.6}
.row2{display:flex;align-items:center;gap:11px;padding:9px 0;border-bottom:1px solid #F1EDE6;font-size:14px}
.row2:last-child{border-bottom:none}
.rank{width:22px;height:22px;border-radius:50%;background:#F3EFE8;color:#6B5D4A;font-size:12px;font-weight:700;display:grid;place-items:center}
.nm{flex:1}.row2 b{color:#C8102E}
</style></head><body><div class="wrap">
<div class="hero">
<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px">
<div><h1 id="heroTitle">顧客回饋中心</h1>
<p class="lead" id="heroLead"></p>
<p class="sub" id="heroSub"></p></div>
<div style="text-align:right;font-size:12.5px;opacity:.85;line-height:1.7"><span id="updatedLbl">資料更新</span><br><b id="asof" style="font-size:14px"></b><br>Marketing &amp; Communications</div>
</div></div>

<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
<div class="tabs" id="tabs"></div>
<label style="font-size:12.5px;color:#5A6272;display:flex;align-items:center;gap:7px">
 <span id="langLabel">語言</span>
 <select id="langSel" onchange="setLang(this.value)" style="padding:6px 9px;border:1px solid #DDD6CC;border-radius:7px;background:#fff;font-size:13px">
  <option value="zh-Hant">繁體中文</option><option value="zh-Hans">简体中文</option><option value="en">English</option>
 </select></label></div>

<div id="home"></div><div id="triage" class="hide"></div>
<div id="insight" class="hide"></div><div id="map" class="hide"></div>
<footer><span id="brandLine"></span><br><span id="footNote"></span></footer>
</div>
<script>
const D=__DATA__;
const ALL_LANGS=__LANGS__;
let LANG=localStorage.getItem("tj_lang")||"zh-Hant";
if(!ALL_LANGS[LANG]) LANG="zh-Hant";
function t(key){const L=ALL_LANGS[LANG]||ALL_LANGS["zh-Hant"];
  if(L[key]!==undefined) return L[key];
  return ALL_LANGS["zh-Hant"][key];}
function fmt(str,vals){return String(str).replace(/\{(\w+)\}/g,function(m,k){return vals[k]!==undefined?vals[k]:m});}
const esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const log={};

function kpi(n,l){return `<div class="kpi"><b>${n}</b><span>${l}</span></div>`}
const THEMES=__THEMES__;
function srcName(k){
  if(LANG==="en") return k==='Xiaohongshu'?'Xiaohongshu':k;
  if(LANG==="zh-Hans") return k==='Xiaohongshu'?'小红书':k;
  return k==='Xiaohongshu'?'小紅書':k;}
function themeName(k){const m=THEMES[LANG]||THEMES["zh-Hant"];return m[k]||k;}
function badge(r){
  if(r.crisis) return '<span class="badge b-crisis">'+esc(t('badge_crisis'))+'</span>';
  return {negative:'<span class="badge b-neg">'+esc(t('badge_neg'))+'</span>',
          positive:'<span class="badge b-pos">'+esc(t('badge_pos'))+'</span>'}[r.senti]
         || '<span class="badge b-neu">'+esc(t('badge_neu'))+'</span>';
}
function fillHero(){
  const lead=document.getElementById('heroLead');
  if(lead) lead.innerHTML=fmt(t('hero_lead'),{pending_neg:D.pending_neg,backlog:D.backlog});
  const asof=document.getElementById('asof');
  if(asof) asof.textContent=D.stats.date_max.slice(0,10);
  const sub=document.getElementById('heroSub');
  if(sub) sub.innerHTML=fmt(t('hero_sub'),{oldest_days:D.oldest_days,oldest_platform:D.oldest_platform});
}
function srcBars(){
  const m=Math.max(...Object.values(D.by_src).map(x=>x.open));
  return Object.entries(D.by_src).sort((a,b)=>b[1].open-a[1].open).map(function(e){
    const k=e[0], v=e[1];
    return '<div class="brow"><div class="bar"><span>'+esc(srcName(k))+'</span>'
      +'<div class="track"><div class="fill" style="width:'+(v.open/m*100)+'%"></div></div>'
      +'<b>'+v.open+'</b></div>'
      +'<div class="bsub">'+esc(fmt(t('waited'),{n:v.med_days}))+' · '+esc(fmt(t('of_which'),{n:v.neg}))+'</div></div>';
  }).join('');
}
function hotRows(){
  return D.hot.map(function(h,i){
    return '<div class="row2"><span class="rank">'+(i+1)+'</span><span class="nm">'+esc(themeName(h[0]))+'</span><b>'+h[1]+' '+esc(t('unit'))+'</b></div>';
  }).join('');
}
function renderHome(){
    const html=''
   +'<div class="kpis">'
   +'<div class="kpi"><b>'+D.pending_neg+'</b><span>'+esc(t('m_complaints'))+'</span><em>'+esc(t('m_complaints_s'))+'</em></div>'
   +'<div class="kpi"><b style="color:#B0342A">'+D.backlog+'</b><span>'+esc(t('m_overweek'))+'</span><em>'+esc(t('m_overweek_s'))+'</em></div>'
   +'<div class="kpi"><b style="color:'+(D.crisis_live?'#C8102E':'#256D46')+'">'+D.crisis_live+'</b><span>'+esc(t('m_crisis'))+'</span><em>'+esc(t('m_crisis_s'))+'</em></div>'
   +'<div class="kpi"><b style="color:#256D46">'+D.pending_pos+'</b><span>'+esc(t('m_praise'))+'</span><em>'+esc(t('m_praise_s'))+'</em></div>'
   +'</div>'
   +'<div class="split">'
     +'<div class="chart"><h2>'+esc(t('h_by_platform'))+'</h2>'+srcBars()
       +'<div class="cap">'+esc(t('median_note'))+'</div></div>'
     +'<div class="chart"><h2>'+esc(t('h_hot'))+'</h2>'+hotRows()
       +'<div class="cap">'+esc(fmt(t('hot_cap'),{pending_neg:D.pending_neg,hot_total:D.hot_total}))+'</div>'
       +'<div class="tip">'+fmt(t('tip'),{backlog:D.backlog,crisis_live:D.crisis_live})+'</div>'
     +'</div>'
   +'</div>';
  document.getElementById('home').innerHTML=html;
}
 function renderTriage(list){
 if(!list)list=D.rows;
 const srcs=[...new Set(D.rows.map(r=>r.src))];
 const ths=[...new Set(D.rows.flatMap(r=>r.themes))];
 document.getElementById('triage').innerHTML=`
 <div class="filters">
  <select id="fSrc"><option value="">'+esc(t('f_platform'))+'</option>${srcs.map(s=>`<option>${esc(s)}</option>`).join('')}</select>
  <select id="fS"><option value="">'+esc(t('f_kind'))+'</option><option value="negative">${esc(t('kind_neg'))}</option><option value="positive">${esc(t('kind_pos'))}</option><option value="neutral">${esc(t('kind_neu'))}</option></select>
  <select id="fT"><option value="">'+esc(t('f_theme'))+'</option>${ths.map(t=>`<option>${esc(t)}</option>`).join('')}</select>
  <label style="align-self:center;font-size:13px"><input type="checkbox" id="fC"> ${esc(t("f_crisis_only"))}</label>
  <input type="search" id="fQ" placeholder="${esc(t('f_search'))}" style="flex:1;min-width:150px">
 </div>
 <div style="font-size:13px;color:#5A6272;margin-bottom:12px">${esc(t('shown')).replace('{a}','<b id="cnt">'+list.length+'</b>').replace('{b}',D.rows.length).replace('{c}','<b id="logn">'+Object.keys(log).length+'</b>')}</div>
 <div id="cards">${list.map((r,i)=>card(r,i)).join('')}</div>`;
 ['fSrc','fS','fT','fC','fQ'].forEach(id=>document.getElementById(id).oninput=apply);
}
function card(r,i){const key=r.url||('row'+i);
 return `<div class="card ${r.crisis?'crisis':''}" data-i="${i}">
 <div class="meta"><span class="src">${esc(srcName(r.src))}</span><b>${esc(r.store)||esc(t('no_store'))}</b><span>${esc(r.date)}</span>
 <span>${esc(t('score'))} <b>${r.pr}</b></span><span>${esc(fmt(t('waiting'),{n:r.days}))}</span><span>${esc(t('reliability'))} ${ t('conf')[r.conf]||r.conf }</span>${badge(r)}</div>
 <div class="body">${esc(r.text)||esc(t('no_text'))}</div>
 <div class="tags">${r.themes.map(t=>`<span>${esc(t)}</span>`).join('')}</div>
 <div class="acts">
  <button class="btn" data-a="reply" ${r.crisis?'disabled':''}>'+esc(t('btn_reply'))+'</button>
  <button class="btn" data-a="esc">'+esc(t('btn_esc'))+'</button>
  <button class="btn" data-a="mon">'+esc(t('btn_mon'))+'</button>
  <button class="btn" data-a="ign">'+esc(t('btn_dis'))+'</button>
  <span class="done" data-done></span>
  ${r.url&&r.url.startsWith('http')?`<a href="${esc(r.url)}" target="_blank" style="font-size:12px">${esc(t('view_source'))} ↗</a>`:''}
 </div></div>`}

function apply(){
 const s=document.getElementById('fSrc').value,v=document.getElementById('fS').value,
       t=document.getElementById('fT').value,c=document.getElementById('fC').checked,
       q=document.getElementById('fQ').value.toLowerCase();
 const out=D.rows.filter(r=>(!s||r.src===s)&&(!v||r.senti===v)&&(!t||r.themes.includes(t))&&(!c||r.crisis)&&(!q||(r.text+r.store).toLowerCase().includes(q)));
 document.getElementById('cards').innerHTML=out.map((r,i)=>card(r,D.rows.indexOf(r))).join('');
 document.getElementById('cnt').textContent=out.length;
 bind();
}
function bind(){document.querySelectorAll('#cards .btn:not(:disabled)').forEach(b=>b.onclick=e=>{
 const cardEl=e.target.closest('.card'),i=+cardEl.dataset.i,r=D.rows[i],key=(r.url||'row'+i)+':'+e.target.dataset.a;
 if(log[key])return; log[key]=1;
 const label={reply:t('done_reply'),esc:t('done_esc'),mon:t('done_mon'),ign:t('done_dis')}[e.target.dataset.a];
 cardEl.querySelector('[data-done]').textContent='✓ '+label;
 document.getElementById('logn').textContent=Object.keys(log).length;});}

function renderInsight(){
 const max=Math.max(...D.themes.map(t=>t[1]));
 document.getElementById('insight').innerHTML=`
 <div class="note">${esc(fmt(t('ins_note'),{negatives:D.negatives.toLocaleString(),silent_negative:D.silent_negative.toLocaleString(),written:D.written.toLocaleString()}))}</div>
 <div class="chart"><h2>投訴原因分佈（全期）</h2>
 ${D.themes.map(([k,v])=>`<div class="bar"><span>${esc(k)}</span><div class="track"><div class="fill" style="width:${v/max*100}%"></div></div><b>${v}</b></div>`).join('')}
 <div class="cap">${esc(fmt(t('ins_cap1'),{written:D.written.toLocaleString()}))}</div></div>
 <div class="chart"><h2>投訴擱置咗幾耐</h2>
 ${(()=>{const vals=D.buckets.map(b=>b[1]);const m=Math.max(...vals)||1;
   return D.buckets.map(b=>'<div class="bar"><span>'+esc(t(b[0]))+'</span><div class="track"><div class="fill" style="width:'+(b[1]/m*100)+'%;background:#D9822B"></div></div><b>'+b[1]+'</b></div>').join('');})()}
 <div class="cap">${esc(fmt(t('ins_cap2'),{latency:D.stats.latency_measurable.toLocaleString()}))}</div></div>`;
}

function renderMap(){
 const lats=D.branches.map(b=>b.lat),lngs=D.branches.map(b=>b.lng);
 const la0=Math.min(...lats),la1=Math.max(...lats),lo0=Math.min(...lngs),lo1=Math.max(...lngs);
 const col=r=>r>=50?'#C62828':r>=30?'#D9822B':r>=15?'#F9A825':'#2E7D32';
 const worst=D.branches.filter(b=>b.n>=10).sort((a,b)=>b.rate-a.rate).slice(0,10);
 document.getElementById('map').innerHTML=`
 <div class="chart"><h2>各分店負面比率（${D.branches.length} 間已識別位置）</h2>
 <div class="map">${D.branches.map(b=>{const x=(b.lng-lo0)/(lo1-lo0)*100,y=(1-(b.lat-la0)/(la1-la0))*100;
  return `<div class="pt" data-t="${esc(b.store)} · ${b.neg}/${b.n} 负面 (${b.rate}%)" style="left:${x}%;top:${y}%;width:${Math.min(30,7+b.n/28)}px;height:${Math.min(30,7+b.n/28)}px;background:${col(b.rate)};opacity:.82"></div>`}).join('')}
 <div style="position:absolute;left:14px;bottom:12px;background:rgba(255,255,255,.92);padding:9px 12px;border-radius:8px;font-size:12px">
  <span class="dot" style="background:#2E7D32"></span>&lt;15% <span class="dot" style="background:#F9A825;margin-left:8px"></span>15–30% <span class="dot" style="background:#D9822B;margin-left:8px"></span>30–50% <span class="dot" style="background:#C62828;margin-left:8px"></span>&gt;50%　${esc(t('legend_size'))}</div></div>
 <div class="note" style="margin-top:14px">${fmt(t('map_unlocated'),{unlocated:'<b>'+D.stats.unlocated.toLocaleString()+'</b>',pct:(D.stats.unlocated/D.stats.total*100).toFixed(1)})}</div>
 <h3>${esc(t('map_worst'))}</h3>
 <table><tr>${t('map_cols').map(function(x){return '<th>'+esc(x)+'</th>'}).join('')}</tr>
 ${worst.map(b=>`<tr><td>${esc(b.store)}</td><td>${b.n}</td><td>${b.neg}</td><td><b style="color:${col(b.rate)}">${b.rate}%</b></td><td>${esc(fmt(t('ago'),{n:b.newest}))}</td></tr>`).join('')}</table>
 <div class="cap">${esc(t('map_worst_cap'))}</div></div>`;
}


function renderTabs(){
 document.getElementById('tabs').innerHTML=t('tabs').map((n,i)=>
   '<div class="tab'+(i===curTab?' on':'')+'" data-v="'+VIEWS[i]+'">'+esc(n)+'</div>').join('');
 document.querySelectorAll('.tab').forEach(el=>el.onclick=()=>{setTab(+VIEWS.indexOf(el.dataset.v))});
}
function setLang(code){LANG=code;localStorage.setItem("tj_lang",code);applyStatic();renderAll();}
function applyStatic(){
 const set=(id,val)=>{const el=document.getElementById(id); if(el&&val!==undefined) el.textContent=val;};
 const html=(id,val)=>{const el=document.getElementById(id); if(el&&val!==undefined) el.innerHTML=val;};
 document.title='譚仔 · '+t('title');
 set('pageTitle','譚仔 · '+t('title'));
 set('heroTitle',t('title'));
 set('langLabel',t('lang_label'));
 const sel=document.getElementById('langSel'); if(sel) sel.value=LANG;
 set('brandLine',t('brand'));
 set('footNote',t('footer_src'));
 set('updatedLbl',t('updated'));
}
const VIEWS=['home','triage','insight','map'];let curTab=0;
function setTab(i){curTab=i;document.querySelectorAll('.tab').forEach((x,j)=>x.classList.toggle('on',j===i));
 VIEWS.forEach((v,j)=>document.getElementById(v).classList.toggle('hide',j!==i));}
function renderAll(){applyStatic();renderTabs();fillHero();renderHome();renderTriage();bind();renderInsight();renderMap();}
renderAll();
</script></body></html>"""

html = html.replace("__DATA__", data).replace("__LANGS__", languages).replace("__THEMES__", themes)
out = pathlib.Path("TamJai_Review_Radar.html")
out.write_text(html, encoding="utf-8")
print(f"wrote {out.name}: {len(html)/1024:.0f} KB")
