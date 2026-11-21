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


# Reply templates keyed by theme, two variants each (warm / formal).
# These encode the brand-voice rules from PRD §5 C4 directly: acknowledge the specific
# issue, state what happens next, make no unverified promise, thank the customer.
# No compensation offer, no naming of staff, no claim that an investigation occurred.
REPLY_TEMPLATES = {
    "queue": [
        ("多謝你嘅耐心等候同留言。尖峰時段等位時間較長，我哋明白呢樣影響用餐體驗。"
         "你提到嘅情況我會轉給相關分店跟進時段安排。如果你再次遇到長時間等位，"
         "歡迎告知我們具體時間同店舖，方便我哋核實。"),
        ("稟謝閣下惠顧及寶貴意見。尖峰時段輪候時間偏長，對造成不便深感抱歉。"
         "我們已將 閣下反映之情況轉達相關門市檢視時段安排。如蒙提供就訪日期與時間，"
         "我們將可作進一步跟進。"),
    ],
    "cleanliness": [
        ("稟謝 閣下指出有關事項，我們非常重視。環境整潔屬基本要求，未能達到標準我們深表歉意。"
         "已將情况轉達所涉門市即時檢視。如有其他細節願意提供，我們將認真跟進。"),
        ("多謝你話我知。整潔係我哋應該做到的基本，你做呢個反映我哋好感謝亦好在意。"
         "已經將情況交俾相關分店即刻檢查。如果方便，話我知大概時間同去咗邊間，等我哋查清楚。"),
    ],
    "delivery_delay": [
        ("對於是次外送延誤，我哋致以誠摯歉意。食物過咗先至送到，體驗一定唔好。"
         "我哋會就外賣訂單嘅出餐同配送環節作出檢視。如可提供訂單日期同時間，"
         "將有助我哋追查具體一單。"),
        ("對延誤造成之不便，我們深表歉意。確保食物適時送達為我方應有之責任。"
         "我们正檢視外賣訂單之備餐與配送流程。如能提供的訂單日期與時間，"
         "我們將可作針對性跟進。"),
    ],
    "delivery_missing": [
        ("很抱歉是次訂單出現缺漏，令你需要額外處理，實在不便。"
         "我哋會就打包與核對環節作出檢視。如方便，請提供訂單日期同時間，"
         "等我哋可以查該單嘅實際情況。"),
        ("就訂單缺漏造成之不便，我們深表歉意。我方正檢視外賣包裝及核對流程，"
         "以減少同類情況再度發生。如蒙提供訂單資料，我們將跟進了解。"),
    ],
    "taste": [
        ("多謝你分享口味上嘅感受。菜式口味存在個人差異，但你提出嘅一點我哋會當認真對待。"
         "已將你嘅意見轉給產品團隊參考。如果有更多想講，歡迎隨時通知。"),
        ("感謝 閣下就食品味道提供之意見。口味雖有個別差異，閣下之反映我們予以重視，"
         "並已轉達相關團隊作為檢討參考。"),
    ],
    "service_attitude": [
        ("对于你describe嘅接待情況，我哋衷心道歉。員工應對客人有禮係基本要求，"
         "未做到我哋冇任何藉口。已將事件轉交負責同事跟進。"
         "如可提供就訪時間同分店，我哋會更具體了解事情。"),
        ("就接待態度方面造成之不快，我們謹致歉意。以禮待客為我方基本原則，"
         "此事我們高度重視，已交由相關人員跟進。如蒙提供到訪日期、時間及門市名稱，"
         "將有助於我們作詳細了解。"),
    ],
    "portion": [
        ("多謝你提出分量方面嘅意見。我哋明白期望與實際有落差會令人失望。"
         "已將反映轉給相關單位作為檢視參考。若你願意提供具體菜式同日期，"
         "我可以查返嗰單嘅情況。"),
        ("就有關份量之分項意見，感謝 閣下提出。我們已將反映轉達相關團隊作檢視參考。"
         "如能提供菜式名稱及就訪日期，我們將可作進一步了解。"),
    ],
    "price": [
        ("多謝你關於價格嘅意見。我哋明白價錢变动會直接影響消費感受。"
         "你嘅反映已經記錄並轉給相關團隊參考。"),
        ("感謝 閣下就定價方面提供之意見。有关反映我們已予記錄，"
         "並轉呈相關團隊於其後檢討時參考。"),
    ],
    "staff_behaviour": [
        ("你所描述嘅員工行為令你有唔好嘅體驗，我哋真心道歉。"
         "已將事件轉交負責同事跟進。如可提供時間同分店，我哋會更具體了解。"),
        ("就有關人員表現導致之不愉快體驗，我們謹致歉意。"
         "此事已交由相關人員跟進。如蒙提供日期、時間及門市資料，必當详细了解。"),
    ],
    "opening_hours": [
        ("多謝你留意到我哋營業時間方面嘅情況。若你到訪時發現未有如預期開業，"
         "確實令人掃興。已將你提供嘅資訊轉給相關門市核實。"),
        ("感謝 閣下就營業時間提供之資訊。如有與公布時間不符之情況，"
         "我們已轉達相關門市予以核實。"),
    ],
    "menu_availability": [
        ("你想食嘅嘢售罄确实掃興，尤其特意過嚟。我哋會將呢個情況反映給相關門市，"
         "檢視熱門時段嘅準備量。多謝你話我知。"),
        ("就 閣下指定貨品供應不足之情況，我們深表遺憾。"
         "已將反映轉達相關門市，以便檢視熱門時段之備貨安排。"),
    ],
}

def _to_hant(text):
    """Force reply text to Traditional before shipping.

    Templates were authored by hand and picked up stray Simplified forms (们, 对, 变, 况)
    plus one variant glyph (峰→峯). Normalising here means a typo in source cannot reach
    a customer-facing draft.
    """
    try:
        from zhconv import convert
        out = convert(text, "zh-hant")
        # 峯 is an orthographic variant of 峰, not a simplified form; the converter
        # prefers it but modern HK usage is 峰. Revert that one substitution.
        return out.replace("尖峯", "尖峰").replace("峯會", "峰會")
    except ImportError:
        return text


def _draft_for(themes):
    """Attach the first matching theme's two variants; crisis items get none."""
    for th in themes:
        if th in REPLY_TEMPLATES:
            return [_to_hant(v) for v in REPLY_TEMPLATES[th]]
    return [_to_hant("感謝你的留言。你的意見已經記錄並轉給相關單位參考。"),
            _to_hant("感謝 閣下之意見。有關事項已予記錄，並轉呈相關單位參照。")]


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
                 url=r.url if isinstance(r.url,str) else "",
                 drafts=_draft_for(list(r.themes))) for _, r in pool.iterrows()]

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
                negatives=len(neg_all), written=len(written),
                districts=json.loads((ROOT / "data" / "districts.json").read_text())
                          if (ROOT / "data" / "districts.json").exists() else [])


data = json.dumps(prepare(), ensure_ascii=False)
languages = json.dumps(LANGS, ensure_ascii=False)
themes = json.dumps(THEMES, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<title id="pageTitle">譚仔 · 顧客回饋中心 | Tam Jai Customer Feedback</title>
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
.dpanel{margin-top:13px;padding:14px;background:#FBF9F6;border:1px solid #E7E2DA;border-radius:10px}
.dpanel h4{font-size:13px;margin:0 0 4px;color:#1A1A1A}
.rules{font-size:11.5px;color:#8A94A6;margin-bottom:11px}
.dv{background:#fff;border:1px solid #EAE5DD;border-radius:9px;padding:11px 13px;margin-bottom:9px}
.dvhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}
.dvhead span{font-size:11.5px;font-weight:700;color:#6B5D4A;letter-spacing:.3px}
.dv p{font-size:13.5px;line-height:1.65;color:#2A3140;margin:0}
.cpy{padding:5px 14px;border:1px solid #C8102E;background:#fff;color:#C8102E;border-radius:7px;
  cursor:pointer;font-size:12px;font-weight:700}
.cpy.ok{background:#2E7D32;border-color:#2E7D32;color:#fff}
.hint{font-size:11.5px;color:#8A94A6;line-height:1.55}
.vm{display:flex;gap:6px;margin-bottom:14px;align-items:center}
.vmb{width:38px;height:32px;display:grid;place-items:center;border:1px solid #DDD6CC;background:#fff;
  border-radius:8px;cursor:pointer;color:#8A94A6;padding:0}
.vmb:hover{color:#5A6272;border-color:#C9C2B7}
.vmb.on{background:#C8102E;border-color:#C8102E;color:#fff}
.vmb svg *{fill:currentColor;stroke:currentColor}
.dgrp{margin:16px 0 0}
.dghead{display:flex;align-items:center;gap:9px;font-size:13px;font-weight:700;color:#1A1A1A;
  padding:7px 0;border-bottom:2px solid #E7E2DA;margin-bottom:7px}
.dghead b{margin-left:auto;color:#C8102E}
.drow{display:flex;gap:11px;align-items:baseline;padding:8px 0;border-bottom:1px solid #F5F2EC;flex-wrap:wrap}
.drow .src{font-size:11px;font-weight:700;background:#EEF1F6;padding:2px 8px;border-radius:5px}
.drow .dim{color:#8A94A6;font-size:11.5px}
.drow .tx{flex:1;min-width:240px;font-size:12.5px;color:#4A5262;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.empty{padding:34px;text-align:center;color:#8A94A6;font-size:13px;background:#FAF8F5;border-radius:10px}
.clr{margin-top:18px;padding:8px 16px;border:1px solid #DDD6CC;background:#fff;border-radius:8px;
  cursor:pointer;font-size:12.5px;color:#8A94A6}
.clr:hover{border-color:#C8102E;color:#C8102E}
.fgrid{display:flex;gap:20px;margin:14px 0}
.fopt{font-size:13.5px;display:flex;gap:7px;align-items:center;cursor:pointer}
#feedTxt{width:100%;min-height:130px;padding:12px;border:1px solid #DDD6CC;border-radius:9px;
  font-family:ui-monospace,Menlo,monospace;font-size:12.5px;line-height:1.6;resize:vertical}
.frow{display:flex;gap:9px;margin:12px 0;flex-wrap:wrap;align-items:center}
.btn.primary{background:#C8102E;color:#fff;border-color:#C8102E;padding:8px 18px;border-radius:8px;
  cursor:pointer;font-size:13px;font-weight:700;border:1px solid #C8102E}
.card.acted{opacity:.5;transition:opacity .35s}
#leaflet{height:520px;border-radius:11px;overflow:hidden;border:1px solid #E7E2DA;margin:12px 0}
.pin span{display:grid;place-items:center;width:100%;height:100%;border-radius:50%;
  color:#fff;font-weight:700;font-size:12px;border:2.5px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.28)}
.pin.r1 span{background:#5FA777}.pin.r2 span{background:#F2C14E;color:#3A3122}
.pin.r3 span{background:#E07A3F}.pin.r4 span{background:#C62828}
.leaflet-container{background:#EDEAE4;font-family:inherit}
.offnote{padding:26px;text-align:center;color:#8A94A6;font-size:13px;background:#F7F4EF;border-radius:10px}
.dimtext{color:#8A94A6;margin-left:6px}
.grid-map{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:16px 0}
.cell{min-height:104px;border-radius:10px;background:#F7F4EF}
.blk{color:#fff;padding:12px 14px;display:flex;flex-direction:column;justify-content:center;transition:transform .15s,box-shadow .15s}
.blk:hover{transform:translateY(-2px);box-shadow:0 5px 16px rgba(0,0,0,.18)}
.bn{font-size:12.5px;font-weight:700;line-height:1.3}
.bv{font-size:27px;font-weight:700;margin:4px 0 2px;letter-spacing:-.5px}
.bs{font-size:11.5px;opacity:.92}
.lgd{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:#5A6272;margin:4px 0 8px}
.lgd i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.cmp{display:flex;align-items:center;gap:12px;padding:10px 13px;border-bottom:1px solid #F1EDE6;font-size:12.5px;flex-wrap:wrap}
.cmp b{color:#1A1A1A}
.cmp .dim{color:#8A94A6}
.cmp .tgls{margin-left:auto;display:flex;gap:5px}
.cmp .tgls i{background:#F3EFE8;color:#6B5D4A;font-style:normal;font-size:11px;padding:2px 8px;border-radius:4px}
.tbl td.tx{max-width:330px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:#5A6272}
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
<div id="done" class="hide"></div>
<div id="feed" class="hide"></div>
<div id="insight" class="hide"></div><div id="map" class="hide"></div>
<footer><span id="brandLine"></span><br><span id="footNote"></span></footer>
</div>
<script>
const DEFAULT_DRAFTS=[["感謝你的留言。你的意見已經記錄並轉給相關單位參考。",
 "感謝 閣下之意見。有關事項已予記錄，並轉呈相關單位參照。"]];
const D=__DATA__;
const ALL_LANGS=__LANGS__;
let LANG=localStorage.getItem("tj_lang")||"zh-Hant";
if(!ALL_LANGS[LANG]) LANG="zh-Hant";
function t(key){const L=ALL_LANGS[LANG]||ALL_LANGS["zh-Hant"];
  if(L[key]!==undefined) return L[key];
  return ALL_LANGS["zh-Hant"][key];}
function fmt(str,vals){return String(str).replace(/\{(\w+)\}/g,function(m,k){return vals[k]!==undefined?vals[k]:m});}
const esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const log=JSON.parse(localStorage.getItem("tj_log")||"{}");
function saveLog(){localStorage.setItem("tj_log",JSON.stringify(log));}

function kpi(n,l){return `<div class="kpi"><b>${n}</b><span>${l}</span></div>`}
const THEMES=__THEMES__;
function srcName(k){
  if(LANG==="en") return k==='Xiaohongshu'?'Xiaohongshu':k;
  if(LANG==="zh-Hans") return k==='Xiaohongshu'?'小红书':k;
  return k==='Xiaohongshu'?'小紅書':k;}
function themeName(k){const m=THEMES[LANG]||THEMES["zh-Hant"];return m[k]||k;}
function badge(r){
  if(r.crisis) return '<span class="badge b-crisis">'+t('badge_crisis')+'</span>';
  return {negative:'<span class="badge b-neg">'+t('badge_neg')+'</span>',
          positive:'<span class="badge b-pos">'+t('badge_pos')+'</span>'}[r.senti]
         || '<span class="badge b-neu">'+t('badge_neu')+'</span>';
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
    return '<div class="row2"><span class="rank">'+(i+1)+'</span><span class="nm">'+esc(themeName(h[0]))+'</span><b>'+h[1]+' '+t('unit')+'</b></div>';
  }).join('');
}
function renderHome(){
    const html=''
   +'<div class="kpis">'
   +'<div class="kpi"><b>'+D.pending_neg+'</b><span>'+t('m_complaints')+'</span><em>'+t('m_complaints_s')+'</em></div>'
   +'<div class="kpi"><b style="color:#B0342A">'+D.backlog+'</b><span>'+t('m_overweek')+'</span><em>'+t('m_overweek_s')+'</em></div>'
   +'<div class="kpi"><b style="color:'+(D.crisis_live?'#C8102E':'#256D46')+'">'+D.crisis_live+'</b><span>'+t('m_crisis')+'</span><em>'+t('m_crisis_s')+'</em></div>'
   +'<div class="kpi"><b style="color:#256D46">'+D.pending_pos+'</b><span>'+t('m_praise')+'</span><em>'+t('m_praise_s')+'</em></div>'
   +'</div>'
   +'<div class="split">'
     +'<div class="chart"><h2>'+t('h_by_platform')+'</h2>'+srcBars()
       +'<div class="cap">'+t('median_note')+'</div></div>'
     +'<div class="chart"><h2>'+t('h_hot')+'</h2>'+hotRows()
       +'<div class="cap">'+esc(fmt(t('hot_cap'),{pending_neg:D.pending_neg,hot_total:D.hot_total}))+'</div>'
       +'<div class="tip">'+fmt(t('tip'),{backlog:D.backlog,crisis_live:D.crisis_live})+'</div>'
     +'</div>'
   +'</div>';
  document.getElementById('home').innerHTML=html;
}
 const ICON_LIST='<svg width="17" height="17" viewBox="0 0 17 17"><rect x="6" y="2" width="9" height="2.4" rx="1.2"/><rect x="6" y="7.3" width="9" height="2.4" rx="1.2"/><rect x="6" y="12.6" width="9" height="2.4" rx="1.2"/><rect x="1.6" y="2" width="2.4" height="2.4" rx="1.2"/><rect x="1.6" y="7.3" width="2.4" height="2.4" rx="1.2"/><rect x="1.6" y="12.6" width="2.4" height="2.4" rx="1.2"/></svg>';
const ICON_CARD='<svg width="17" height="17" viewBox="0 0 17 17"><rect x="1.5" y="1.5" width="6.2" height="6.2" rx="1.6"/><rect x="9.3" y="1.5" width="6.2" height="6.2" rx="1.6"/><rect x="1.5" y="9.3" width="6.2" height="6.2" rx="1.6"/><rect x="9.3" y="9.3" width="6.2" height="6.2" rx="1.6"/></svg>';
const ICON_TABLE='<svg width="17" height="17" viewBox="0 0 17 17"><path d="M1.5 2.5h14M1.5 7h14M1.5 11.5h14M1.5 15h14" stroke-width="1.6" fill="none"/><path d="M6.5 2.5V15" stroke-width="1.6"/></svg>';

let vmMode=localStorage.getItem("tj_vm")||"card";
function renderTriage(list){
 if(!list)list=D.rows;
 const srcs=[]; D.rows.forEach(function(r){if(srcs.indexOf(r.src)<0)srcs.push(r.src);});
 const ths=[]; D.rows.forEach(function(r){r.themes.forEach(function(x){if(ths.indexOf(x)<0)ths.push(x)})});
 const el=document.getElementById('triage');
 el.innerHTML=''
  +'<div class="filters">'
    +'<select id="fSrc"><option value="">'+esc(t('f_platform'))+'</option>'
      +srcs.map(function(x){return '<option>'+esc(x)+'</option>'}).join('')+'</select>'
    +'<select id="fS"><option value="">'+esc(t('f_kind'))+'</option>'
      +'<option value="negative">'+esc(t('kind_neg'))+'</option>'
      +'<option value="positive">'+esc(t('kind_pos'))+'</option>'
      +'<option value="neutral">'+esc(t('kind_neu'))+'</option></select>'
    +'<select id="fT"><option value="">'+esc(t('f_theme'))+'</option>'
      +ths.map(function(x){return '<option>'+esc(x)+'</option>'}).join('')+'</select>'
    +'<label style="align-self:center;font-size:13px"><input type="checkbox" id="fC"> '
      +esc(t('f_crisis_only'))+'</label>'
    +'<input type="search" id="fQ" placeholder="'+esc(t('f_search'))+'" style="flex:1;min-width:150px">'
  +'</div>'
  +'<div style="font-size:13px;color:#5A6272;margin-bottom:12px">'
    +esc(t('shown')).replace('{a}','<b id="cnt">'+list.length+'</b>')
      .replace('{b}',D.rows.length).replace('{c}','<b id="logn">'+Object.keys(log).length+'</b>')
  +'</div>'
  +'<div class="vm" id="vmBar">'
    +[['compact',ICON_LIST,t('vm_compact')],['card',ICON_CARD,t('vm_card')],['table',ICON_TABLE,t('vm_table')]]
      .map(function(m){return '<button class="vmb'+(vmMode===m[0]?' on':'')+'" data-m="'+m[0]+'" title="'+esc(m[2])
        +'" aria-label="'+esc(m[2])+'">'+m[1]+'</button>'}).join('')
  +'</div>'
  +'<div id="cards">'+renderList(list)+'</div>';
 ['fSrc','fS','fT','fC','fQ'].forEach(function(id){document.getElementById(id).oninput=apply});
 document.querySelectorAll('#vmBar .vmb').forEach(function(btn){btn.onclick=function(){
   vmMode=btn.dataset.m; localStorage.setItem("tj_vm",vmMode); renderTriage();}});
}
function renderList(list){
 if(vmMode==="table"){
   return '<table class="tbl"><tr>'+t('cols').map(function(c){return '<th>'+esc(c)+'</th>'}).join('')+'</tr>'
     +list.map(function(r){return '<tr><td>'+esc(srcName(r.src))+'</td><td>'+(esc(r.store)||esc(t('no_store')))
        +'</td><td>'+esc(r.date)+'</td><td>'+r.pr+'</td><td>'+r.days+'</td><td>'+badge(r)
        +'</td><td class="tx">'+esc(String(r.text||'').slice(0,90))+'</td></tr>'}).join('')+'</table>';
 }
 if(vmMode==="compact"){
   return list.map(function(r,i){return '<div class="cmp" data-i="'+i+'">'
     +'<b>'+esc(srcName(r.src))+'</b><span>'+esc(r.store||t('no_store'))+'</span>'
     +'<span class="dim">'+esc(r.date)+'</span><span class="dim">'+esc(t('score'))+' '+r.pr+'</span>'
     +'<span class="dim">'+esc(fmt(t('waiting'),{n:r.days}))+'</span>'
     +'<span class="tgls">'+r.themes.map(function(x){return '<i>'+esc(x)+'</i>'}).join('')+'</span>'
     +badge(r)+'</div>'}).join('');
 }
 return list.map(function(r,i){return card(r,i)}).join('');
}
function card(r,i){
 return '<div class="card'+(r.crisis?' crisis':'')+'" data-i="'+i+'">'
  +'<div class="meta"><span class="src">'+esc(srcName(r.src))+'</span><b>'+(esc(r.store)||esc(t('no_store')))+'</b>'
    +'<span>'+esc(r.date)+'</span>'
    +'<span>'+esc(t('score'))+' <b>'+r.pr+'</b></span>'
    +'<span>'+esc(fmt(t('waiting'),{n:r.days}))+'</span>'
    +'<span>'+esc(t('reliability'))+' '+esc((t('conf')[r.conf])||r.conf)+'</span>'
    +badge(r)+'</div>'
  +'<div class="body">'+(esc(r.text)||esc(t('no_text')))+'</div>'
  +'<div class="tags">'+(r.themes.length?r.themes.map(function(x){return '<span>'+esc(x)+'</span>'}).join(' ')
      :'<span>'+esc(t('untagged'))+'</span>')+'</div>'
  +'<div class="acts">'
    +'<button class="btn" data-a="reply"'+(r.crisis?' disabled':'')+'>'+esc(t('btn_reply'))+'</button>'
    +'<button class="btn" data-a="esc">'+esc(t('btn_esc'))+'</button>'
    +'<button class="btn" data-a="mon">'+esc(t('btn_mon'))+'</button>'
    +'<button class="btn" data-a="ign">'+esc(t('btn_dis'))+'</button>'
    +'<span class="done" data-done></span>'
    +(r.url&&String(r.url).indexOf('http')===0?'<a href="'+esc(r.url)+'" target="_blank" style="font-size:12px">'+esc(t('view_source'))+' ↗</a>':'')
  +'</div></div>';
}
function openDraft(cardEl,r){
 const d=r.drafts||[];
 const wrap=document.createElement('div');wrap.className='dpanel';
 wrap.innerHTML='<h4>'+esc(t('draft_title'))+'</h4>'
   +'<div class="rules">'+esc(t('draft_rules')).replace('{n}',(r.themes||[]).join('、'))+'</div>'
   +d.map(function(v,i){
     return '<div class="dv"><div class="dvhead"><span>'+esc(i===0?t('v_warm'):t('v_formal'))+'</span>'
       +'<button class="cpy" data-v="'+i+'">'+esc(t('copy'))+'</button></div>'
       +'<p>'+esc(v)+'</p></div>'}).join('')
   +'<div class="hint">'+esc(t('draft_hint'))+'</div>';
 cardEl.appendChild(wrap);
 wrap.querySelectorAll('.cpy').forEach(function(btn){btn.onclick=function(){
   const txt=d[+btn.dataset.v];
   navigator.clipboard.writeText(txt).then(function(){
     btn.textContent=t('copied');btn.classList.add('ok');
     setTimeout(function(){btn.textContent=t('copy');btn.classList.remove('ok')},1800);},
   function(){ // clipboard API blocked over http: fall back to selection
     const ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);
     ta.select();try{document.execCommand('copy');btn.textContent=t('copied')}catch(e){btn.textContent=t('copy_fail')}
     document.body.removeChild(ta);setTimeout(function(){btn.textContent=t('copy')},1800);});
 }});
}
function renderDone(){
 const keys=Object.keys(log);
 const rows=keys.map(function(k){const i=+k.split(":")[0];return {r:D.rows[i],a:k.split(":")[1]}}).filter(function(x){return x.r});
 const el=document.getElementById('done');
 if(!rows.length){el.innerHTML='<div class="chart"><h2>'+esc(t('done_h'))+'</h2>'
   +'<div class="empty">'+esc(t('done_empty'))+'</div></div>';return;}
 const groups={reply:[],esc:[],mon:[],ign:[]};
 rows.forEach(function(x){(groups[x.a]=groups[x.a]||[]).push(x.r)});
 const meta={reply:['badge_pos',t('btn_reply')],esc:['badge_crisis',t('btn_esc')],
             mon:['badge_neu',t('btn_mon')],ign:['badge_neu',t('btn_dis')]};
 el.innerHTML='<div class="chart"><h2>'+esc(t('done_h'))+'（'+rows.length+'）</h2>'
  +'<div class="cap">'+esc(t('done_note'))+'</div>'
  +Object.keys(groups).filter(function(k){return groups[k].length}).map(function(k){
    return '<div class="dgrp"><div class="dghead"><span>'+esc(meta[k][1])+'</span><b>'+groups[k].length+'</b></div>'
     +groups[k].slice(0,40).map(function(r){return '<div class="drow">'
       +'<span class="src">'+esc(srcName(r.src))+'</span><span>'+esc(r.store||t('no_store'))+'</span>'
       +'<span class="dim">'+esc(r.date)+'</span><span class="tx">'+esc(String(r.text||'').slice(0,86))+'</span></div>'}).join('')
     +(groups[k].length>40?'<div class="cap">… '+esc(t('more_than'))+' '+(groups[k].length-40)+'</div>':'')+'</div>'}).join('')
  +'<button class="clr" onclick="clearDone()">'+esc(t('clear_done'))+'</button></div>';
}
function clearDone(){if(confirm(t('clear_confirm'))){localStorage.removeItem("tj_log");location.reload();}}
function apply(){
 const sel=document.getElementById('fSrc').value, kind=document.getElementById('fS').value,
       th=document.getElementById('fT').value, onlyC=document.getElementById('fC').checked,
       q=document.getElementById('fQ').value.toLowerCase();
 const seen={}; Object.keys(log).forEach(function(k){seen[k.split(':')[0]]=1});
 const out=D.rows.filter(function(r){
   if(seen[D.rows.indexOf(r)])return false;
   return (!sel||r.src===sel) && (!kind||r.senti===kind) && (!th||r.themes.indexOf(th)>=0)
     && (!onlyC||r.crisis) && (!q||(String(r.text)+String(r.store)).toLowerCase().indexOf(q)>=0);
 });
 document.getElementById('cards').innerHTML=renderList(out);
 const cnt=document.getElementById('cnt'); if(cnt) cnt.textContent=out.length;
 bind();
}
function bind(){document.querySelectorAll('#cards .btn[data-a="reply"]:not(:disabled)').forEach(b=>b.onclick=function(e){
 const c=e.target.closest('.card'),i=+c.dataset.i,r=D.rows[i];
 if(c.querySelector('.dpanel')){c.querySelector('.dpanel').remove();return;}
 openDraft(c,r);});
document.querySelectorAll('#cards .btn:not([data-a="reply"]):not(:disabled)').forEach(b=>b.onclick=e=>{
 const cardEl=e.target.closest('.card'),i=+cardEl.dataset.i,r=D.rows[i],key=(r.url||'row'+i)+':'+e.target.dataset.a;
 if(log[key])return; log[key]=1; saveLog();
 const label={reply:t('done_reply'),esc:t('done_esc'),mon:t('done_mon'),ign:t('done_dis')}[e.target.dataset.a];
 cardEl.querySelector('[data-done]').textContent='✓ '+label;
 document.getElementById('logn').textContent=Object.keys(log).length;
   var cd=e.target.closest('.card'); if(cd) setTimeout(function(){cd.classList.add('acted')},350);});}

function renderFeed(){
 document.getElementById('feed').innerHTML=
   '<div class="chart"><h2>'+esc(t('feed_h'))+'</h2>'
  +'<div class="cap">'+esc(t('feed_intro'))+'</div>'
  +'<div class="fgrid">'
    +'<label class="fopt"><input type="radio" name="fmode" value="paste" checked> '+esc(t('feed_paste'))+'</label>'
    +'<label class="fopt"><input type="radio" name="fmode" value="file"> '+esc(t('feed_file'))+'</label>'
  +'</div>'
  +'<textarea id="feedTxt" placeholder="'+esc(t('feed_ph'))+'"></textarea>'
  +'<input type="file" id="feedFile" accept=".csv,.txt" style="display:none">'
  +'<div class="frow"><select id="feedSrc">'+['OpenRice','Xiaohongshu','Google Maps','Threads'].map(function(x){
      return '<option>'+esc(x)+'</option>'}).join('')+'</select>'
    +'<button class="btn primary" onclick="ingest()">'+esc(t('feed_go'))+'</button>'
    +'<button class="btn" onclick="dlTemplate()">'+esc(t('feed_tpl'))+'</button></div>'
  +'<div class="cap" id="feedMsg">'+esc(t('feed_note'))+'</div></div>';
 document.querySelectorAll('input[name=fmode]').forEach(function(rb){rb.onchange=function(){
   var paste=this.value==='paste';
   document.getElementById('feedTxt').style.display=paste?'block':'none';
   document.getElementById('feedFile').style.display=paste?'none':'inline-block';}});
}
function dlTemplate(){
 var rows=[["platform","date","branch","text"],
   ["OpenRice","2026-11-20","Mong Kok","\u7b49\u4e86\u4e00\u500b\u9418\u624d\u6709\u6a71\u4f4d\uff0c\u670d\u52d9\u54e1\u6c92\u5f88\u597d\u5730\u9053\u6b49\u3002"]];
 var csv=rows.map(function(r){return r.join(',')}).join(String.fromCharCode(10));
 var a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 a.download='tamjai_import_template.csv';a.click();
}
function ingest(){
 var mode=document.querySelector('input[name=fmode]:checked').value;
 var src=document.getElementById('feedSrc').value;
 var raw=mode==='paste'?document.getElementById('feedTxt').value:'';
 if(mode==='file'){var f=document.getElementById('feedFile').files[0];
   if(!f){setFeedMsg(t('feed_nofile'));return;}
   var rd=new FileReader();rd.onload=function(){addRows(rd.result,src)};rd.readAsText(f);return;}
 addRows(raw,src);
}
function addRows(raw,src){
 if(!raw.trim()){setFeedMsg(t('feed_empty'));return;}
 var added=0;
 raw.split(String.fromCharCode(10)).forEach(function(lineRaw,idx){
   var line=String(lineRaw).split(String.fromCharCode(13)).join('');
   if(idx===0&&(line.toLowerCase().indexOf('platform')>=0||line.indexOf('\u5e73\u53f0')>=0))return;
   var c=line.split(',');
   if(c.length<4)return;
   var text=c.slice(3).join(',').replace(/^"|"$/g,'').trim();
   if(text.length<2)return;
   D.rows.unshift({src:src,store:c[2].trim(),date:c[1].trim(),text:text,themes:[],
     senti:'negative',pr:60,days:0,conf:'medium',crisis:false,url:'',drafts:DEFAULT_DRAFTS});
   added++;});
 setFeedMsg(added?t('feed_ok').replace('{n}',added):t('feed_none'));
 if(added){renderTriage();renderHome();}
}
function setFeedMsg(m){document.getElementById('feedMsg').textContent=m;}
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
 const el=document.getElementById('map');
 const B=D.branches||[];
 el.innerHTML='<div class="chart"><h2>'+esc(fmt(t('map_h'),{branches:B.length}))+'</h2>'
   +'<div id="leaflet"></div>'
   +'<div class="lgd">'+[[0,"<20%"],[20,"20–25%"],[25,"25–30%"],[30,"≥30%"]].map(function(x){
       return '<span><i style="background:'+colRate(x[0])+'"></i>'+x[1]+' 投訴</span>'}).join('')
   +'<span class="dimtext">'+esc(t('legend_size'))+'</span></div>'
   +'<div class="cap">'+esc(t('map_note'))+'</div></div>'
   +'<div class="chart"><h2>'+esc(t('map_worst'))+'</h2>'
   +'<table><tr>'+t('map_cols').map(function(c){return '<th>'+esc(c)+'</th>'}).join('')+'</tr>'
   +B.filter(function(b){return b.n>=10}).sort(function(a,c){return c.rate-a.rate}).slice(0,12).map(function(d){
     return '<tr><td>'+esc(d.store)+'</td><td>'+d.n+'</td><td>'+d.neg+'</td>'
       +'<td><b style="color:'+colRate(d.rate)+'">'+d.rate+'%</b></td>'
       +'<td>'+esc(fmt(t('ago'),{n:d.newest}))+'</td></tr>'}).join('')+'</table>'
   +'<div class="cap">'+esc(fmt(t('map_worst_cap')))+'</div>'
   +'<div class="cap">'+esc(fmt(t('map_unlocated'),{unlocated:D.stats.unlocated.toLocaleString(),
      pct:(D.stats.unlocated/D.stats.total*100).toFixed(1)}))+'</div></div>';

 if(typeof L==="undefined"){document.getElementById('leaflet').innerHTML='<div class="offnote">'
   +esc(t('map_offline'))+'</div>';return;}
 const map=L.map('leaflet',{scrollWheelZoom:false}).setView([22.31,114.17],10);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
   attribution:'© OpenStreetMap contributors', maxZoom:19, crossOrigin:true}).addTo(map);
 B.forEach(function(d){
   const size=Math.min(46,22+Math.log(Math.max(1,d.n))*7);
   const icon=L.divIcon({className:'pin r'+rateBand(d.rate),
     html:'<span>'+d.n+'</span>',iconSize:[size,size],iconAnchor:[size/2,size/2]});
   L.marker([d.lat,d.lng],{icon:icon}).addTo(map)
    .bindPopup('<b>'+esc(d.store)+'</b><br>'+d.n+' 則評論 · '+d.neg+' 則投訴（'+d.rate+'%）');
 });
}
function rateBand(r){return r>=30?"4":r>=25?"3":r>=20?"2":"1";}
function colRate(r){return r>=30?"#C62828":r>=25?"#E07A3F":r>=20?"#F2C14E":"#5FA777";}


function renderTabs(){
 document.getElementById('tabs').innerHTML=t('tabs').map((n,i)=>
   '<div class="tab'+(i===curTab?' on':'')+'" data-v="'+VIEWS[i]+'">'+esc(n)+'</div>').join('');
 document.querySelectorAll('.tab').forEach(el=>el.onclick=()=>{setTab(+VIEWS.indexOf(el.dataset.v))});
}
function setLang(code){LANG=code;localStorage.setItem("tj_lang",code);applyStatic();renderAll();}
function applyStatic(){
 const set=(id,val)=>{const el=document.getElementById(id); if(el&&val!==undefined) el.textContent=val;};
 const html=(id,val)=>{const el=document.getElementById(id); if(el&&val!==undefined) el.innerHTML=val;};
 document.title=t('brand_short')+' · '+t('title');

 set('heroTitle',t('title'));
 set('langLabel',t('lang_label'));
 const sel=document.getElementById('langSel'); if(sel) sel.value=LANG;
 set('brandLine',t('brand'));
 set('footNote',t('footer_src'));
 set('updatedLbl',t('updated'));
}
const VIEWS=['home','triage','done','feed','insight','map'];let curTab=0;
function setTab(i){curTab=i;document.querySelectorAll('.tab').forEach((x,j)=>x.classList.toggle('on',j===i));
 VIEWS.forEach((v,j)=>document.getElementById(v).classList.toggle('hide',j!==i));}
function renderAll(){applyStatic();renderTabs();fillHero();renderHome();renderTriage();bind();renderInsight();renderMap();}
renderAll();
</script></body></html>"""

html = html.replace("__DATA__", data).replace("__LANGS__", languages).replace("__THEMES__", themes)
out = pathlib.Path("TamJai_Review_Radar.html")
out.write_text(html, encoding="utf-8")
print(f"wrote {out.name}: {len(html)/1024:.0f} KB")
