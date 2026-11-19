# Tam Jai Customer Feedback Centre · 譚仔顧客回饋中心

HKBU PRAO3086 Group I — Direction 1: The Responder.

Aggregates public comments about Tam Jai International from OpenRice, Xiaohongshu,
Google Maps and Threads into one ranked triage queue, with theme analysis and a
per-branch performance map. No reply is ever published by the system.

## Open it
Deployed live at the URL shown in the "Deploy" section above this text.

## What is inside
| File | Role |
|---|---|
| `app.py` | Entry point — the four views |
| `landing.py` | Home screen markup |
| `analyzer.py` | Rule engine: themes, crisis detection, priority score |
| `naming.py` | Branch-name normalisation and territory lookup |
| `build_cache.py` | Rebuilds `data/` from the source spreadsheets (not needed to run) |
| `data/analysed.parquet` | Pre-computed results for 19,055 comments |

## Notes on the numbers
Sentiment uses each platform's own published rating where one exists; themes and crisis
flags come from deterministic rules, so results are reproducible and explainable.
Comments that name no branch are reported separately rather than guessed onto the map.
