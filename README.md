# Tam Jai Review Radar — what I built, and what the data actually says

Live app: **http://localhost:8555** (running now)

## Run it

```bash
cd tamjai_app
PYTHONPATH=../pdftmp python3 build_cache.py      # re-analyse the four xlsx files
PYTHONPATH=../pdftmp python3 -m streamlit run app.py
```

`build_cache.py` reads your four Excel exports, applies the rule engine, writes
`data/analysed.parquet`. The app only reads that parquet — **no network calls at runtime**,
so a demo cannot fail on an outage. This matches PRD §4.4 (batch jobs, not streaming).

---

## The four things the data taught me that the plan did not anticipate

### 1. "譚仔" is not always the restaurant

Searching Threads for 譚仔 returns the **蔡天鳳 murder case**, where 譚仔 is the defendant's
son's media nickname. 865 rows (4.5%) are court-commentary, not customer feedback. Counting
them as complaints would have inflated negative volume by roughly a fifth of the Threads set.

I added a relevance gate (`analyzer.is_relevant`). It filters 0% of OpenRice and Google Maps
— correct, because those records come from branch-bound pages — and removes the murder-case
posts from Threads.

**This is the strongest story in the whole project.** It is exactly the R2-style trap: a naive
pipeline produces confident numbers that are simply wrong, and nothing looks broken.

### 2. Half the corpus has no words

9,927 rows (52%) are star ratings with no text — overwhelmingly Google Maps. So:

- **Sentiment coverage is good** (stars give us feeling for everyone)
- **Reason coverage is thin** (only ~4,300 negative comments actually say why)

The Insights page now shows these separately instead of blending them into one misleading
theme chart.

### 3. Age does not mean unanswered

My first version treated anything older than 180 days as "unanswered". That was wrong:
OpenRice (99%) and Google Maps (98%) return their **entire review history** — some rows go
back to 2003. A 2015 complaint is not six years unanswered; it is archived.

So latency is now reported **only where it can be measured**: Threads and Xiaohongshu, which
are complete recent snapshots (1,234 comments). Everything else contributes to themes but
makes no latency claim.

### 4. Coordinates beat address parsing

Street addresses ("Jaffe Rd", "Po Lun St") contain no district name, so name matching left
67% of Google Maps rows unclassified. Territory now comes from lat/lng bands read off your
actual store coordinates, giving Kowloon 60 / New Territories 39 / HK Island 6 across 105
branches — which matches how Tam Jai is really distributed.

---

## What each view does

| View | What it answers | Honest limits shown on screen |
|---|---|---|
| **Triage Queue** | Which comment do I handle first? 632 items in the 90-day window, ranked by severity × age × engagement. Crisis cards disable *Reply*. | Confidence label per card; "low" appears on 11,618 rows and is never hidden |
| **Insights** | What are customers demanding? Theme bars split stated reasons vs silent ratings; monthly sentiment lines; latency histogram restricted to measurable sources | Relevance filter count, coverage warning, denominator on every chart |
| **Store Map** | Which branches look weakest? 99 located branches coloured by % negative, sized by volume; worst-performers table | Unlocated band stated as 1,326 comments (7.0%); branches under n=10 excluded from the ranking |

Crisis handling works as specified: 108 flagged items across the corpus, 7 inside the current
window. Their *Reply* button is disabled and only *Escalate to Ops* is offered. Nothing
publishes — actions write to an in-session audit log and say so.

---

## Bugs I found and fixed during the build

Worth knowing because they were real, not hypothetical:

1. **Theme patterns over-matched.** `少[左佐]?` fired on "少辣" (mild spice) and "妖左我"; bare
   `缺` fired on "缺點". This produced 1,472 fake delivery complaints on dine-in reviews.
   Tightened to require delivery context → 103.
2. **Parquet turns lists into numpy arrays**, so `r["themes"] or []` raised `ValueError` mid-render.
   Caught only by Streamlit's own AppTest runner — my hand-written stub had masked it. Normalised
   at load.
3. **Recency model conflated archive with backlog** (see above).
4. **Territory via address text** failed on two-thirds of rows.

---

## Still deliberately simple

No login system, no database server, no live API. The PRD said two people and four weeks;
this honours that. If you want the Week 13 deliverable to include real LLM drafting, C4 would
be the one component to wire to DeepSeek — everything else gains nothing from it.

## Two things I could not verify

- **Screenshot rendering.** Headless Chrome never completes Streamlit's websocket handshake, so
  it captured a loading skeleton rather than the UI. Correctness was proven through AppTest
  (all three views, zero exceptions) instead. **Open http://localhost:8555 yourself before
  presenting.**
- **Whether Threads' 1,150 rows are a fair sample.** They are all within the window and 65% are
  replies. If the collection method favoured recent activity, Threads will dominate the fresh
  queue disproportionately. Worth checking how it was exported.
