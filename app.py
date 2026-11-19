"""譚仔顧客回饋中心 — Streamlit front end.

Four views: 今日工作 / 待回覆 / 趨勢分析 / 分店表現.
Reads data/analysed.parquet produced by build_cache.py. No network calls at runtime, so a
demo cannot fail on an outage or a cold API.

Design note: every figure states its own denominator, and nothing is phrased as a claim about
the product. A communications manager should read the top of page one and know what to do
this morning.
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from naming import is_generic
from i18n_generated import LANGS, THEMES

ROOT = Path(__file__).parent

THEME_ZH = {
    "queue": "排隊輪候", "cleanliness": "衛生環境", "service_attitude": "服務態度",
    "taste": "口味品質", "price": "價格性價比", "portion": "分量",
    "opening_hours": "營業時間／結業", "delivery_delay": "外送延誤",
    "delivery_missing": "漏送缺品", "staff_behaviour": "員工行為",
    "menu_availability": "貨品供應", "other": "其他",
}
SRC_ZH = {"Google Maps": "Google Maps", "OpenRice": "OpenRice",
          "Xiaohongshu": "小紅書", "Threads": "Threads"}


@st.cache_data(show_spinner=False)
def load():
    df = pd.read_parquet(ROOT / "data" / "analysed.parquet")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Parquet stores list columns as numpy arrays; `arr or []` then raises ValueError.
    df["themes"] = [list(t) if t is not None else [] for t in df["themes"]]
    return df


def derived(df):
    """Everything the home page needs, computed once."""
    ref = df["date"].max()
    d = df.assign(days=(ref - df["date"]).dt.days.clip(lower=0))
    live = d[d.relevant & (d.days <= 90)]
    neg = live[live.sentiment == "negative"]
    pos = live[live.sentiment == "positive"]
    per_src = {}
    for src, g in live.groupby("source"):
        per_src[SRC_ZH.get(src, src)] = dict(
            open=int(len(g)), med=int(g.days.median()), avg=int(g.days.mean()),
            neg=int((g.sentiment == "negative").sum()))
    written = neg[neg.text.str.strip().str.len() >= 5]
    hot = Counter(t for ts in written.themes for t in ts if t != "other")
    return dict(
        live=live, neg=neg, pos=pos,
        pending_neg=len(neg), pending_pos=len(pos),
        backlog=int((neg.days > 7).sum()), crisis=int(live.crisis.sum()),
        oldest=int(neg.days.max()) if len(neg) else 0,
        oldest_src=SRC_ZH.get(neg.sort_values("days", ascending=False).iloc[0].source, "—") if len(neg) else "—",
        per_src=per_src, hot=hot, hot_written=len(written))


st.set_page_config(page_title="譚仔 · 顧客回饋中心", layout="wide", initial_sidebar_state="expanded")

df = load()
stats = json.loads((ROOT / "data" / "stats.json").read_text())
V = derived(df)

LANG = st.sidebar.selectbox(
    "語言" if True else "",
    ["繁體中文", "简体中文", "English"],
    index=0, key="lang_sel", label_visibility="visible")
CODE = {"繁體中文": "zh-Hant", "简体中文": "zh-Hans", "English": "en"}[LANG]


def fmt(text, **vals):
    for k, v in vals.items():
        text = str(text).replace("{" + k + "}", str(v))
    return text


def t(key):
    """Look up a UI string, falling back to Traditional rather than showing a raw key."""
    L = LANGS.get(CODE, LANGS["zh-Hant"])
    return L.get(key, LANGS["zh-Hant"].get(key, key))


def theme(k):
    m = THEMES.get(CODE, THEMES["zh-Hant"])
    return m.get(k, k)


def src(name):
    """Platform names stay as brands in Chinese; Xiaohongshu localises."""
    if CODE == "en":
        return "Xiaohongshu" if name == "Xiaohongshu" else name
    if CODE == "zh-Hans":
        return "小红书" if name == "Xiaohongshu" else name
    return "小紅書" if name == "Xiaohongshu" else name


st.sidebar.markdown(f"**Tam Jai International**  \n**{t('title')}**")
TABS = [t("tabs")[i] for i in range(4)]
view = st.sidebar.radio(t("lang_label") and TABS[0], TABS, label_visibility="collapsed")
st.sidebar.caption(
    f"{t('updated')} {stats['date_max'][:10]}  \n"
    f"{stats['total']:,} {t('unit')} · 4 platforms  \n\n"
    f"{t('footer_src')}")

# ------------------------------------------------------------------ 今日工作
if view == TABS[0]:
    st.markdown(f"## {t('title')}")
    st.markdown(
        "**" + fmt(t("hero_lead"), pending_neg=V["pending_neg"], backlog=V["backlog"]) + "**  \n"
        + fmt(t("hero_sub"), oldest_days=V["oldest"], oldest_platform=V["oldest_src"]))

    c = st.columns(4)
    c[0].metric(t("m_complaints"), V["pending_neg"], help=t("m_complaints_s"))
    c[1].metric(t("m_overweek"), V["backlog"], help=t("m_overweek_s"))
    c[2].metric(t("m_crisis"), V["crisis"], help=t("m_crisis_s"))
    c[3].metric(t("m_praise"), V["pending_pos"], help=t("m_praise_s"))

    left, right = st.columns(2)
    with left:
        st.subheader(t("h_by_platform"))
        rows = sorted(V["per_src"].items(), key=lambda x: -x[1]["open"])
        mx = max(v["open"] for _, v in rows)
        for name, v in rows:
            st.markdown(
                f"<div style='margin:0 0 10px'>"
                f"<div style='font-size:13px;color:#5A6272'>{name}　<b style='color:#1A1A1A'>{v['open']}</b> 則</div>"
                f"<div style='background:#F3EFE8;border-radius:4px;height:18px'>"
                f"<div style='width:{v['open']/mx*100:.0f}%;height:18px;background:#2F6B45;border-radius:4px'></div></div>"
                f"<div style='font-size:11.5px;color:#8A94A6'>中位已擱 {v['med']} 日 · 當中投訴 {v['neg']} 則</div>"
                f"</div>", unsafe_allow_html=True)
        st.caption(t("median_note"))

    with right:
        st.subheader(t("h_hot"))
        for i, (k, n) in enumerate(V["hot"].most_common(6), 1):
            st.markdown(
                f"<div style='display:flex;align-items:center;padding:7px 0;border-bottom:1px solid #F1EDE6'>"
                f"<span style='width:22px;height:22px;border-radius:50%;background:#F3EFE8;color:#6B5D4A;"
                f"display:grid;place-items:center;font-size:12px;font-weight:700;margin-right:10px'>{i}</span>"
                f"<span style='flex:1;font-size:14px'>{THEME_ZH.get(k, k)}</span>"
                f"<b style='color:#C8102E'>{n} 則</b></div>", unsafe_allow_html=True)
        st.caption(fmt(t("hot_cap"), pending_neg=V["pending_neg"], hot_total=V["hot_written"]))

    st.info("**" + t("tip").replace("<b>建議優先處理：</b>", "").strip() + "**")

# ------------------------------------------------------------------ 待回覆
elif view == TABS[1]:
    st.header(TABS[1])
    pool = V["neg"].sort_values("priority", ascending=False).head(500)

    names = sorted({SRC_ZH.get(s, s) for s in V["live"].source})
    f_src = st.multiselect(t("f_platform"), names, default=names)
    f_theme = st.selectbox(t("f_theme"), [t("all_option")] + sorted({THEME_ZH.get(t, t) for ts in pool.themes for t in ts}))
    f_only_crisis = st.checkbox(t("f_crisis_only"), False)
    q = st.text_input(t("f_search"), "")

    work = pool.copy()
    work["src_zh"] = work.source.map(SRC_ZH)
    if f_src:
        work = work[work.src_zh.isin(f_src)]
    if f_theme != "全部":
        rev = {v: k for k, v in THEME_ZH.items()}
        key = rev.get(f_theme, f_theme)
        work = work[work.themes.map(lambda x: key in x)]
    if f_only_crisis:
        work = work[work.crisis]
    if q:
        work = work[work.text.str.contains(q, case=False, na=False) |
                    work.store.astype(str).str.contains(q, case=False, na=False)]

    st.caption(f"顯示 {len(work)} / {len(pool)} 則 · 按 嚴重度 × 擱置日數 × 互動量 排序")

    CONF = t("conf")
    for _, r in work.head(40).iterrows():
        with st.container(border=True):
            h = st.columns([1, 1.4, 0.9, 0.9, 1.1, 1.3])
            h[0].markdown(f"**{SRC_ZH.get(r.source, r.source)}**")
            h[1].markdown(r.store if isinstance(r.store, str) and r.store.strip() else t("no_store"))
            h[2].markdown(r.date.strftime("%Y-%m-%d") if pd.notna(r.date) else "")
            h[3].markdown(f"優先分 **{r.priority:.0f}**")
            h[4].markdown(fmt(t("waiting"), n=int(r.days_open)))
            h[5].markdown(t("badge_crisis") if bool(r.crisis) else
                          {"negative": t("badge_neg"), "positive": t("badge_pos")}.get(r.sentiment, t("badge_neu")))

            txt = (r.text or "").strip().replace("\n", " ")
            st.markdown(txt[:300] + ("…" if len(txt) > 300 else "") or t('no_text'))
            tags = " ".join(f"`{THEME_ZH.get(t, t)}`" for t in r.themes) or f"`{t('untagged')}`"
            st.caption(f"{tags}   ·   {t('reliability')}：{CONF.get(r.confidence, r.confidence)}")

            b = st.columns([1, 1, 1, 1, 2])
            b[0].button(t("btn_reply"), disabled=bool(r.crisis), key=f"rp{abs(hash((r.url, str(r.text))))}")
            b[1].button(t("btn_esc"), key=f"es{abs(hash((r.url, str(r.text))))}")
            b[2].button(t("btn_mon"), key=f"mo{abs(hash((r.url, str(r.text))))}")
            b[3].button(t("btn_dis"), key=f"ig{abs(hash((r.url, str(r.text))))}")
            if isinstance(r.url, str) and r.url.startswith("http"):
                b[4].markdown(f"[睇原文 ↗]({r.url})")

    st.warning(t("demo_note"))

# ------------------------------------------------------------------ 趨勢分析
elif view == TABS[2]:
    st.header(TABS[2])
    neg_all = df[df.relevant & (df.sentiment == "negative")]
    written = neg_all[neg_all.text.str.strip().str.len() >= 5]
    silent = len(neg_all) - len(written)

    st.info(fmt(t("ins_note"), negatives=f"{len(neg_all):,}",
                silent_negative=f"{silent:,}", written=f"{len(written):,}"))

    a, b = st.columns(2)
    with a:
        st.subheader(t("ins_reasons"))
        tc = Counter(t for ts in written.themes for t in ts if t != "other")
        s = pd.Series(dict(tc)).sort_values().tail(9)
        adf = pd.DataFrame({"count": s.values, "theme": [THEME_ZH.get(i, i) for i in s.index]})
        fig = px.bar(adf, x="count", y="theme", orientation="h", text="count",
                     color_discrete_sequence=["#2F6B45"], labels={"theme": "", "count": "則數"})
        fig.update_layout(height=420, margin=dict(l=10, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(fmt(t("ins_cap1"), written=f"{len(written):,}"))

    with b:
        st.subheader("主題隨時間變化")
        m = written.copy()
        m["month"] = m.date.dt.to_period("M").astype(str)
        top5 = [k for k, _ in tc.most_common(5)]
        exploded = (m.assign(theme=m.themes.map(lambda x: [THEME_ZH.get(t, t) for t in x if t in top5]))
                    .explode("theme").dropna(subset=["theme"]))
        piv = exploded.groupby(["month", "theme"]).size().unstack(fill_value=0).tail(12)
        lf = piv.reset_index().melt(id_vars="month", var_name="theme", value_name="count")
        fig = px.line(lf, x="month", y="count", color="theme", markers=True)
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=20), legend_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader(t("ins_latency"))
    meas = df[df.latency_measurable & df.relevant & (df.sentiment == "negative")]
    buckets = ["一週內", "一至四週", "一至三個月"]
    ldf = pd.DataFrame({"age": buckets, "comments": [
        int((meas.days_open <= 7).sum()),
        int(((meas.days_open > 7) & (meas.days_open <= 30)).sum()),
        int(((meas.days_open > 30) & (meas.days_open <= 90)).sum())]})
    fig = px.bar(ldf, x="age", y="comments", text="comments", color_discrete_sequence=["#D9822B"],
                 labels={"age": "", "comments": "則數"})
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(fmt(t("ins_cap2"), latency=f"{len(meas):,}"))

# ------------------------------------------------------------------ 分店表現
else:
    st.header(TABS[3])
    geo = df[df.lat.notna() & ~df.store.map(is_generic)].copy()
    g = (geo.groupby(["store", "lat", "lng"])
         .agg(n=("text", "size"), neg=("sentiment", lambda x: int((x == "negative").sum())),
              newest=("days_open", "min")).reset_index())
    g["rate"] = (g.neg / g.n * 100).round(1)

    # Branch labels repeat across Google Maps listings ("譚仔雲南米線 TamJai Yunnan Mixian"
    # appears on several sites), so collapse by location and keep the largest sample.
    g = g.sort_values("n", ascending=False).groupby(["lat", "lng"], as_index=False).first()

    # Scattermapbox requires scalar textfont size and numeric marker size; NaN here
    # raised a hard AttributeError on Streamlit Cloud while working locally.
    for col in ("n", "neg"):
        g[col] = pd.to_numeric(g[col], errors="coerce").fillna(0).astype(int)
    big = g[g.n >= 40].copy()
    small = g[g.n < 40].copy()

    def scale(v, lo, hi):
        v = np.asarray(v, dtype=float)
        return lo + (v - v.min()) / max(1e-6, v.max() - v.min()) * (hi - lo)

    fig = px.scatter_mapbox(
        big, lat="lat", lon="lng", color="rate",
        color_continuous_scale=[[0, "#2E7D32"], [0.15, "#F9A825"], [0.25, "#D9822B"], [0.35, "#C62828"]],
        range_color=[0, 45], zoom=10.3, center={"lat": 22.31, "lon": 114.17},
        mapbox_style="open-street-map", hover_name="store",
        hover_data={"n": True, "neg": True, "rate": ":.1f", "newest": True, "lat": False, "lng": False},
        labels={"rate": "投訴比率%", "n": "評論數", "neg": "投訴", "newest": "最新一則（日前）"})
    fig.update_traces(marker=dict(size=scale(big.n, 16, 46), opacity=0.9))
    fig.add_trace(go.Scattermapbox(
        lat=big.lat, lon=big.lng, mode="text", text=big.n.astype(str),
        textfont=dict(size=13, color="white"), textposition="middle center",
        showlegend=False, hoverinfo="skip"))
    if len(small):
        fig.add_trace(go.Scattermapbox(
            lat=small.lat, lon=small.lng, mode="markers",
            marker=dict(size=8, opacity=0.55, color=small.rate,
                        colorscale=[[0, "#2E7D32"], [1, "#C62828"]], cmin=0, cmax=45),
            customdata=small[["store", "n", "rate"]],
            hovertemplate="%{customdata[0]}<br>%{customdata[1]} 則 · 投訴 %{customdata[2]:.1f}%<extra></extra>",
            name="樣本較少的分店"))
    fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("map_note"))

    st.subheader(t("map_worst"))
    worst = g[g.n >= 10].sort_values("rate", ascending=False).head(12)[["store", "n", "neg", "rate", "newest"]]
    worst.columns = ["分店", "評論數", "投訴", "投訴比率%", "最新一則（日前）"]
    st.dataframe(worst, use_container_width=True, hide_index=True)
    st.caption("少於 10 則評論的分店不列入排行——樣本過小時，單一的差評屬噪音而非結論。")

    st.warning(f"另有 **{stats['unlocated']:,} 則無法歸類到分店**（{stats['unlocated']/stats['total']*100:.1f}%）。"
               "小紅書與 Threads 的貼文常只提及「譚仔」而未說明分店，而全港有兩百多間門市無從判斷。"
               "這類記錄沒有被推測歸類，因此地圖並非完整覆蓋——閱讀數字時須留意。")

