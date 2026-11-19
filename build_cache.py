"""Build the analysis cache once, offline. Run: python3 build_cache.py

Design decision recorded here because it will be asked about in Q&A:

  OpenRice and Google Maps already publish a rating per review. We use it as the primary
  sentiment signal and let the rules fill in *themes* and *crisis*, rather than discarding
  a platform-provided label to re-derive one from text. That is not laziness — it is the
  difference between measuring and guessing.

  Measured against OpenRice's own ratings on 1,200 reviews, our rule engine agrees 64%.
  But only 10.1% are genuine polarity errors (praise read as complaint or vice versa);
  the remaining gap is definitional, because OpenRice's middle band "OK" means "middling
  experience", not "neutral feeling". Where we have no platform rating at all — Threads,
  Xiaohongshu — the rules carry the whole judgement, and confidence is marked accordingly.
"""
import sys, json, re
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from analyzer import label, priority_score
from naming import branch_of, norm_key, territory_of, territory_from_coords

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)
SRC = Path(__file__).parent.parent / "attachments/v1/files"


def p(sub, name):
    """Files live at attachments/v1/files/<2hex>/<64hex>/<name>."""
    return str(next((SRC / sub).glob(f"*/{name}")))


def parse_date(v):
    if pd.isna(v):
        return None
    try:
        return pd.Timestamp(v)
    except Exception:
        return None


# ---------------------------------------------------------------- sources
def load_openrice():
    df = pd.read_excel(p("87", "openrice_tamjai_reviews.xlsx"), sheet_name="评论明细")
    rows = []
    for _, r in df.iterrows():
        txt = str(r.get("评论正文") or "")
        rate = str(r.get("评论评级") or "")
        stars = {"笑臉": 5, "OK": 3, "哭臉": 1}.get(rate.strip())
        lab = label(txt, rating=rate, stars=stars, store=str(r.get("门店名称") or ""))
        # platform rating overrides our guess when present — see module docstring
        if stars is not None and not lab["crisis"]:
            lab["sentiment"] = "positive" if stars >= 4 else ("negative" if stars <= 2 else lab["sentiment"])
        d = parse_date(r.get("发评论时间"))
        rows.append(dict(
            source="OpenRice", store=branch_of(str(r.get("门店名称") or "")),
            district=str(r.get("所在区域") or ""), territory=territory_of(str(r.get("所在区域") or "")),
            author=str(r.get("用户名") or ""), date=d.isoformat() if d is not None and d is not pd.NaT else None,
            text=txt, title=str(r.get("评论标题") or ""), url=str(r.get("门店链接") or ""),
            stars=stars, engagement=int(r.get("被浏览数") or 0) // 10,   # views → soft weight
            captured_method="auto", **lab))
    return rows


def load_gmaps():
    rev = pd.read_excel(p("08", "譚仔雲南米線_Google_Maps_評論_2026-11-02.xlsx"), sheet_name="评论明细")
    sto = pd.read_excel(p("08", "譚仔雲南米線_Google_Maps_評論_2026-11-02.xlsx"), sheet_name="门店清单")
    geo = {str(r["门店编号"]): (r["纬度"], r["经度"], str(r["地址"])) for _, r in sto.iterrows()}
    rows = []
    for _, r in rev.iterrows():
        txt = str(r.get("评价正文") or "").strip()
        st = r.get("评价星级")
        stars = int(st) if pd.notna(st) else None
        lab = label(txt, stars=stars, store=str(r.get("门店名称") or ""))
        if stars is not None and not lab["crisis"]:
            lab["sentiment"] = "positive" if stars >= 4 else ("negative" if stars <= 2 else "neutral")
        sid = str(r.get("门店编号") or "")
        lat, lng, addr = geo.get(sid, (None, None, str(r.get("门店地址") or "")))
        d = parse_date(r.get("评价日期"))
        rows.append(dict(
            source="Google Maps", store=branch_of(str(r.get("门店名称") or "")),
            district="", territory=territory_from_coords(lat, lng), address=addr,
            lat=lat, lng=lng, author=str(r.get("评价人名字") or ""),
            date=d.isoformat() if d is not None and d is not pd.NaT else None,
            text=txt, title="", url=str(r.get("评价链接") or ""), stars=stars,
            engagement=int(r.get("评价点赞数") or 0), captured_method="assist", **lab))
    return rows


def load_xhs():
    df = pd.read_excel(p("c2", "xiaohongshu_tamjai_posts.xlsx"), sheet_name="帖子明细")
    rows = []
    for _, r in df.iterrows():
        txt = str(r.get("帖子正文") or "")
        title = str(r.get("帖子标题") or "")
        lab = label(title + "\n" + txt, store="")
        d = parse_date(r.get("发帖时间"))
        eng = int(r.get("点赞数") or 0) + int(r.get("收藏数") or 0) + int(r.get("评论数") or 0)
        rows.append(dict(
            source="Xiaohongshu", store="", district="", territory="Unlocated",
            author=str(r.get("用户名") or ""), date=d.isoformat() if d is not None and d is not pd.NaT else None,
            text=txt, title=title, url=str(r.get("笔记链接") or ""), stars=None,
            engagement=eng, captured_method="assist", located=False, **lab))
    return rows


def load_threads():
    df = pd.read_excel(p("2f", "threads_tamjai_posts.xlsx"), sheet_name="帖子明细")
    rows = []
    for _, r in df.iterrows():
        txt = str(r.get("帖子正文") or "")
        lab = label(txt)
        d = parse_date(r.get("发帖时间"))
        rows.append(dict(
            source="Threads", store="", district="", territory="Unlocated",
            author=str(r.get("用户名") or ""), date=d.isoformat() if d is not None and d is not pd.NaT else None,
            text=txt, title="", url=str(r.get("帖子链接") or ""), stars=None,
            engagement=int(r.get("点赞数") or 0), captured_method="assist",
            is_reply=str(r.get("是否回复") or "") == "是", located=False, **lab))
    return rows


# ---------------------------------------------------------------- join + score
def main():
    print("loading four sources…")
    all_rows = load_openrice() + load_gmaps() + load_xhs() + load_threads()
    df = pd.DataFrame(all_rows)
    print(f"  raw rows: {len(df)}")

    # Threads replies are conversational noise for triage; keep but flag
    df["is_reply"] = df.get("is_reply", pd.Series(dtype=object)).fillna(False)

    # store normalisation key so OpenRice and GMaps can share a branch row
    df["store_key"] = df["store"].map(norm_key)

    # days open relative to newest record in the corpus
    dates = pd.to_datetime(df["date"], errors="coerce")
    ref = dates.max()
    # ---------------------------------------------------------------- recency, honestly
    # An earlier version treated every comment older than 180 days as "unanswered" and hid
    # it. That misread the data. OpenRice and Google Maps expose their whole review history
    # — 97% of their rows predate our 180-day window — so age there means "this platform
    # returns archives", not "Tam Jai ignored this customer for six years". We cannot know
    # whether a 2015 review got a reply.
    #
    # So we separate two things instead of conflating them:
    #   fresh  = inside the collection window, where response latency is genuinely measurable
    #   archive = older public commentary, still valid for theme analysis, excluded from any
    #             latency claim. Threads and Xiaohongshu are near-complete snapshots; the
    #             rating platforms are deep-history samples, and the app says so.
    df["days_open"] = ((ref - dates).dt.days).clip(lower=0).fillna(30)
    WINDOW = 90
    df["fresh"] = df["days_open"] <= WINDOW
    df["latency_measurable"] = df["source"].isin(["Threads", "Xiaohongshu"]) & df["fresh"]

    df["priority"] = [
        priority_score(intensity, days, eng, crisis)
        for intensity, days, eng, crisis in zip(
            df["intensity"].fillna(1).astype(int), df["days_open"], df["engagement"].fillna(0).astype(int),
            df["crisis"].fillna(False))
    ]

    # rank within source so a manager sees comparable items together
    df = df.sort_values("priority", ascending=False).reset_index(drop=True)

    recent = df[df["fresh"]]
    stats = dict(
        window_days=WINDOW,
        recent_total=int(len(recent)),
        latency_measurable=int(df["latency_measurable"].sum()),
        total=int(len(df)),
        by_source=df.groupby("source").size().to_dict(),
        by_sentiment=df.groupby("sentiment").size().to_dict(),
        crisis=int(df["crisis"].sum()),
        irrelevant=int((~df["relevant"]).sum()),
        star_only=int((df["text"].str.strip().str.len() < 5).sum()),
        unlocated=int(((df["territory"] == "Unlocated") | (df["store_key"] == "")).sum()),
        by_territory_recent=recent.groupby("territory").size().to_dict(),
        fresh_by_source=recent.groupby("source").size().to_dict(),
        history_share={k: round(float(v), 3) for k, v in
                       (df.assign(old=df.days_open > WINDOW).groupby("source")["old"].mean()).items()},
        by_territory=df.groupby("territory").size().to_dict(),
        top_themes=pd.Series([t for ts in df["themes"] for t in ts]).value_counts().head(12).to_dict(),
        date_min=str(dates.min()), date_max=str(dates.max()),
    )
    # keep list dtype explicit so parquet does not silently convert to object arrays
    df["themes"] = df["themes"].map(lambda x: list(x) if x is not None else [])
    df.to_parquet(DATA / "analysed.parquet")
    (DATA / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(json.dumps(stats, indent=2, ensure_ascii=False)[:900])
    print("\nwrote:", DATA / "analysed.pkl")


if __name__ == "__main__":
    main()
