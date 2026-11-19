"""Tam Jai Review Radar — Streamlit front end.

Three views, matching PRD §4: V1 Triage Queue, V2 Insights, and the district map.
Data comes from data/analysed.parquet produced by build_cache.py; nothing here calls a
network API, so the app is reproducible and cannot fail during a demo.
"""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).parent
THEME_ZH = {
    "queue": "排隊", "cleanliness": "衛生", "service_attitude": "服務態度", "taste": "口味",
    "price": "價格", "portion": "分量", "opening_hours": "營業時間", "delivery_delay": "配送延誤",
    "delivery_missing": "漏送", "staff_behaviour": "員工行為", "menu_availability": "供貨", "other": "其他",
}


@st.cache_data(show_spinner=False)
def load():
    df = pd.read_parquet(ROOT / "data" / "analysed.parquet")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Parquet stores list columns as numpy arrays; `arr or []` then raises ValueError.
    # Convert once here so downstream code can treat themes as an ordinary list.
    df["themes"] = [list(t) if t is not None else [] for t in df["themes"]]
    return df


def theme_counts(df):
    from collections import Counter
    c = Counter(t for ts in df["themes"] for t in ts)
    return c


st.set_page_config(page_title="Tam Jai Review Radar", layout="wide", initial_sidebar_state="expanded")
df = load()
stats = json.loads((ROOT / "data" / "stats.json").read_text())

st.sidebar.markdown("**TAM JAI**  \n**REVIEW RADAR**")
VIEWS = ["Home", "Triage Queue", "Insights", "Store Map"]
view = st.sidebar.radio("View", VIEWS)
st.sidebar.caption(
    f"{stats['total']:,} comments · 4 platforms\n"
    f"collected {stats['date_min'][:10]} → {stats['date_max'][:10]}\n\n"
    "Sentiment from platform ratings where published;\n"
    "themes and crisis flags from rule engine C1–C3.\n"
    "No auto-publishing anywhere in this product."
)

# ------------------------------------------------------------------ TRIAGE QUEUE
if view == "Home":
    import landing
    landing.render(st, df, stats)

elif view == "Triage Queue":
    st.header("Triage Queue")
    st.caption("Ranked by severity × days unanswered × engagement. Crisis items are flagged and never drafted.")

    work = df[df["fresh"] & df["relevant"]].copy()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Comments in {stats['window_days']}-day window", f"{len(work):,}")
    col2.metric("Negative", f"{int((work.sentiment=='negative').sum()):,}")
    col3.metric("Crisis flagged", f"{int(work.crisis.sum()):,}", delta=None)
    if len(work):
        oldest = work.sort_values("days_open", ascending=False).iloc[0]
        col4.metric("Oldest in window", f"{int(oldest.days_open)} d")
    else:
        col4.metric("Oldest in window", "–")

    f_src = st.multiselect("Platform", sorted(work.source.unique()), default=sorted(work.source.unique()))
    f_sent = st.selectbox("Sentiment", ["any", "negative", "neutral", "positive"])
    f_theme = st.selectbox("Theme", ["any"] + sorted(THEME_ZH))
    f_crisis = st.checkbox("Crisis only", False)

    q = work[work.source.isin(f_src)]
    if f_sent != "any":
        q = q[q.sentiment == f_sent]
    if f_theme != "any":
        q = q[q["themes"].map(lambda x: f_theme in x)]
    if f_crisis:
        q = q[q.crisis]
    q = q.sort_values("priority", ascending=False).head(60)

    st.write(f"**{len(q)}** of {len(work):,} shown (top 60 by priority)")
    if q.empty:
        st.info("No comments match these filters. Widen the platform or sentiment selection.")
        st.stop()
    for _, r in q.iterrows():
        with st.container(border=True):
            head = st.columns([0.9, 1.5, 1.0, 0.9, 1.4])
            head[0].markdown(f"**{r.source}**")
            store_lbl = r.store.strip() if isinstance(r.store, str) and r.store.strip() else "—"
            head[1].markdown(store_lbl)
            head[2].markdown(r.date.strftime("%Y-%m-%d") if pd.notna(r.date) else "")
            head[3].markdown(f"score **{r.priority:.1f}** · {int(r.days_open)}d")
            badge = "🔴 CRISIS" if bool(r.crisis) else {"negative": "⚠ negative", "positive": "✅ positive"}.get(r.sentiment, "○ neutral")
            head[4].markdown(badge)

            txt = (r.text or "").strip().replace("\n", " ")
            st.markdown((txt[:300] + "…") if len(txt) > 300 else (txt or "(star rating only)"))

            thm = r["themes"]
            try:
                thm = list(thm) if thm is not None else []
            except TypeError:
                thm = []
            tags = " ".join(f"`{THEME_ZH.get(t,t)}`" for t in thm) or "`—`"
            conf = r.confidence
            st.caption(f"{tags}   ·   confidence: {conf}")

            acts = st.columns([1, 1, 1, 1, 3])
            if r.crisis:
                acts[0].button("Reply 🚫", disabled=True, key=f"rp{r.name if hasattr(r,'name') else id(r)}")
                if acts[1].button("Escalate to Ops", key=f"es{abs(hash((r.url,r.text)))}"):
                    st.session_state.setdefault("log", []).append(("escalated", r.url))
            else:
                if acts[0].button("Reply", key=f"rp{abs(hash((r.url,r.text)))}"):
                    st.session_state.setdefault("log", []).append(("reply", r.url))
            if acts[2].button("Monitor", key=f"mo{abs(hash((r.url,r.text)))}"):
                st.session_state.setdefault("log", []).append(("monitor", r.url))
            if acts[3].button("Ignore", key=f"ig{abs(hash((r.url,r.text)))}"):
                st.session_state.setdefault("log", []).append(("ignore", r.url))
            acts[4].caption(f"[source link]({r.url})" if isinstance(r.url, str) and r.url.startswith("http") else "")

    n = len(st.session_state.get("log", []))
    st.success(f"{n} action(s) recorded to the audit log this session. Nothing was published — approval and posting stay human.")

# ------------------------------------------------------------------ INSIGHTS
elif view == "Insights":
    st.header("Insights")
    work = df[df["fresh"] & df["relevant"]]
    hist = df[~df["fresh"]]
    tc = theme_counts(df[df.fresh & df.relevant])
    neg = work[work.sentiment == "negative"]
    tcn = theme_counts(neg)

    st.caption("Every figure below states its denominator. Themes come from a closed list of twelve, so weeks are comparable.")
    st.info(f"**Relevance filter.** {int((~df.relevant).sum()):,} rows matched the search term but concern something else — chiefly Threads chatter about the 蔡天鳳 murder case, where 譚仔 is the defendant's son's nickname, not the restaurant. Those are excluded from every figure on this page.\n\n**What this window is.** {stats['recent_total']:,} comments fall inside {stats['window_days']} days. "
            f"OpenRice ({int(stats['history_share']['OpenRice']*100)}%) and Google Maps "
            f"({int(stats['history_share']['Google Maps']*100)}%) return their whole review history, so most of their rows are older than the window — that is how those platforms expose data, not evidence of unanswered complaints. "
            f"Response latency is therefore reported only for the {stats['latency_measurable']:,} comments where we can actually measure it (Threads and Xiaohongshu snapshots).")

    rel = df[df.relevant]
    neg_all = rel[rel.sentiment == "negative"]
    # "other" is dominated by low-star Google Maps ratings that carry no words at all.
    # Reporting it as the top complaint would be misleading; split it into stated vs silent.
    silent = int((neg_all.text.str.strip().str.len() < 5).sum())
    all_tcn = theme_counts(neg_all)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Stated reasons among negative comments")
        # drop "other" from the bar: it is a bucket, not a complaint, and it dwarfs everything
        shown = {k: v for k, v in all_tcn.items() if k != "other"}
        s = pd.Series(shown).sort_values(ascending=True).tail(10)
        adf = pd.DataFrame({"count": s.values, "theme": [THEME_ZH.get(i, i) for i in s.index]})
        fig = px.bar(adf, x="count", y="theme", orientation="h", text="count",
                     color_discrete_sequence=["#2F6B45"],
                     title=f"n = {len(neg_all):,} negative · {silent:,} gave a rating but no words",
                     labels={"theme": ""})
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Themes in the recent window (text-bearing only)")
        tc2 = {k: v for k, v in tc.items() if k != "other"}
        s2 = pd.Series(tc2).sort_values(ascending=True).tail(10)
        tdf = pd.DataFrame({"count": s2.values, "theme": [THEME_ZH.get(i, i) for i in s2.index]})
        fig = px.bar(tdf, x="count", y="theme", orientation="h", text="count",
                     color_discrete_sequence=["#D9822B"],
                     title=f"n = {len(work):,} within {stats['window_days']} days",
                     labels={"theme": ""})
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly volume by sentiment (all periods)")
    m = df.copy()
    m["month"] = m["date"].dt.to_period("M").astype(str)
    piv = m.groupby(["month", "sentiment"]).size().unstack(fill_value=0).tail(14)
    lfig = px.line(piv.reset_index().melt(id_vars="month", var_name="sentiment", value_name="count"),
                   x="month", y="count", color="sentiment", markers=True)
    lfig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10),
                       legend_title="", title=None)
    st.plotly_chart(lfig, use_container_width=True)
    n_silent = int((df["text"].str.strip().str.len() < 5).sum())
    st.caption(f"{n_silent:,} rows are star-only ratings with no text — mostly Google Maps. They count in sentiment volume but cannot contribute a theme, which is why bar totals sit below the line-chart totals.")

    st.subheader("Response latency")
    bins = [0, 7, 30, 90, 180]
    labels = ["≤1 week", "1–4 weeks", "1–3 months", "3–6 months"]
    meas = df[df.latency_measurable & df.relevant & (df.sentiment == "negative")]
    buckets = ["≤1 week", "1–4 weeks", "1–3 months"]
    lat = pd.cut(meas["days_open"], bins=[0, 7, 30, 90], labels=buckets, right=False)
    ldf = pd.DataFrame({"age": buckets, "comments": [int((lat == b).sum()) for b in buckets]})
    fig = px.bar(ldf, x="age", y="comments", text="comments", color_discrete_sequence=["#C62828"],
                 title=f"age of open negative comments where latency is measurable (n = {len(meas):,})",
                 labels={"age": "", "comments": "comments"})
    fig.update_layout(height=280)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Restricted to Threads and Xiaohongshu because those are complete recent snapshots. "
               "Applying this to OpenRice or Google Maps would misreport archived history as unanswered complaints.")

    st.markdown(
        f"""**Reading these two numbers together.** Of {len(neg_all):,} negative comments,
        **{silent:,} carry no text at all** — they are one- or two-star Google Maps ratings.
        So the theme bars describe the complaints customers *chose to write down*, while the
        star count describes everyone who was unhappy. Where the two disagree, the gap is the
        real signal: a branch can look calm in themes and still sit at 2.7 stars.""")

    st.warning("**Coverage limits.** "
               f"{stats['unlocated']:,} comments could not be attributed to a branch, and "
               f"{stats['by_source']['Threads']:,} Threads rows are replies rather than posts. "
               "Conclusions describe what we read, not all commentary about Tam Jai.")

# ------------------------------------------------------------------ STORE MAP
else:
    st.header("Store Map")
    st.caption("Mean severity per branch. Only comments that name a branch contribute; the rest sit in the unlocated band below.")

    geo = df[df.lat.notna() & df.relevant].copy()
    if len(geo):
        g = geo.groupby(["store", "lat", "lng"]).agg(
            n=("text", "size"),
            neg=("sentiment", lambda s: int((s == "negative").sum())),
            cri=("crisis", "sum"),
            score=("priority", "mean"),
        ).reset_index()
        g["neg_rate"] = (g.neg / g.n * 100).round(1)

        m = px.scatter_mapbox(
            g, lat="lat", lon="lng", size=g.n.clip(lower=1), color="neg_rate",
            color_continuous_scale=["#2E7D32", "#F9A825", "#C62828"], range_color=[0, 60],
            hover_name="store", hover_data=["n", "neg", "cri", "neg_rate"],
            mapbox_style="carto-positron", zoom=10, center={"lat": 22.31, "lon": 114.16},
            labels={"neg_rate": "% negative"}, title=f"{len(g)} branches located · {len(geo):,} comments (all periods)",
        )
        m.update_layout(height=620, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(m, use_container_width=True)

        st.subheader("Worst-performing branches by negative share")
        worst = g[g.n >= 10].sort_values("neg_rate", ascending=False).head(12)[["store", "n", "neg", "neg_rate", "cri"]]
        st.dataframe(worst, use_container_width=True, hide_index=True)
        st.caption("Branches with fewer than 10 recent comments are excluded — one bad review at n=3 is noise, not signal.")

    unloc = stats["unlocated"]
    pct = round(unloc / stats["total"] * 100, 1)
    st.info(f"**Unlocated band: {unloc:,} comments ({pct}%).** Xiaohongshu and Threads rarely name a branch, and a post about “譚仔” could describe any of roughly 219 stores. Rather than guess these onto a map, they are held out and counted here.")
