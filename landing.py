"""Landing page markup, kept out of app.py so the styling stays readable."""
import pandas as pd


def render(st, df, stats):
    st.markdown(
        """
        <style>
        .hero { background: linear-gradient(135deg,#C8102E 0%,#7A0C1B 100%);
                color:#fff; padding:2.3rem 2rem; border-radius:14px; margin-bottom:1.5rem; }
        .hero h1 { font-size:2.25rem; margin:0 0 .55rem 0; color:#fff; letter-spacing:-.6px; }
        .hero p  { font-size:1.1rem; opacity:.95; margin:.3rem 0; line-height:1.5; }
        .card { background:#fff; border:1px solid #E7E2DA; border-radius:12px;
                padding:1.15rem 1.25rem; height:100%; }
        .card h3 { margin:0 0 .4rem 0; font-size:1.02rem; color:#1A1A1A; }
        .card p  { margin:0; font-size:.88rem; color:#5A6272; line-height:1.55; }
        .num { font-size:1.85rem; font-weight:700; color:#C8102E; margin:0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hero">
          <h1>Tam Jai Review Radar</h1>
          <p><b>Four platforms. One ranked queue. Nothing published without a person approving it.</b></p>
          <p style="opacity:.86;font-size:.98rem">Customers already talk about Tam Jai on OpenRice,
          Xiaohongshu, Google Maps and Threads. The problem was never silence &mdash; it was that no one
          could read all four rooms at once.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    located = len(df[df.lat.notna()].store.unique())
    c = st.columns(4)
    cards = [
        (f"{stats['total']:,}", "comments collected", "across four public platforms"),
        (f"{stats['irrelevant']:,}", "filtered out as irrelevant",
         "search hits about the 蔡天鳳 case, not the restaurant"),
        (f"{stats['crisis']:,}", "crisis-flagged",
         "food safety, allergy or legal claims &mdash; never drafted automatically"),
        (f"{located:,}", "branches located",
         "from coordinates, with unlocated commentary held out"),
    ]
    for col, (num, head, sub) in zip(c, cards):
        col.markdown(
            f'<div class="card"><p class="num">{num}</p>'
            f"<p><b>{head}</b><br>{sub}</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown("### Three things this tool does")
    k = st.columns(3)
    k[0].markdown(
        '<div class="card"><h3>1 &middot; Tell you what to look at first</h3>'
        "<p>A ranked triage queue, ordered by severity &times; how long it has sat &times; engagement. "
        "Every card carries four actions. Crisis cards lose the Reply button by design.</p></div>",
        unsafe_allow_html=True,
    )
    k[1].markdown(
        '<div class="card"><h3>2 &middot; Separate stated complaints from silent ones</h3>'
        f"<p>{stats['star_only']:,} rows are a star rating with no words at all. We report those apart, "
        "because blending them would make a branch look understood when it is only scored.</p></div>",
        unsafe_allow_html=True,
    )
    k[2].markdown(
        '<div class="card"><h3>3 &middot; Show which branches look weakest</h3>'
        "<p>A district map coloured by negative share, excluding branches with too few comments to say "
        f"anything, and stating that {stats['unlocated']:,} comments could not be located.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### What we will not do")
    st.markdown(
        "- **No auto-publishing.** There is no publish button anywhere in this product. A manager "
        "copies approved text and posts it herself, then logs the time.\n"
        "- **No customer chatbot.** Our user is a communications manager, not a diner.\n"
        "- **No guessing.** Comments naming no branch stay in an unlocated band rather than being "
        "placed on a map."
    )
    st.caption(
        f"Data window {stats['date_min'][:10]} \u2192 {stats['date_max'][:10]} · "
        f"{stats['window_days']}-day working window for live triage · themes drawn from a closed list "
        "of twelve so weeks remain comparable · built for HKBU PRAO3086 Group I"
    )
