---
name: stock-snapshot
description: This skill should be used when the user wants to look up a ticker's fund status — is it eligible for the Base or Potential sleeve, what did it score, why — alongside its financial trend chart, from this project's cached fundamentals (cache/stocks_data/*.json). Triggers on phrasing like "look up", "show me", "fund status", "is X eligible", "what's X's score", for any ticker in either index (SP500 or TASE125), not just current fund holdings.
version: 0.1.0
disable-model-invocation: false
---

# Stock Snapshot

Generates a self-contained HTML Artifact combining two things for one ticker: a **Fund
Status card** (eligibility for the Base and Potential sleeves, recomputed live from the
cached fundamentals with a per-criterion breakdown, plus the score breakdown if the stock
was scored in the last full build or quarterly update) and the **same Financial Trends
chart** produced by the `stock-financials-chart` skill — reused via direct import, not
rebuilt.

## When to use this

Any time the user wants to know whether a ticker qualifies for the fund, why, or how it
scored — not just what its P&L looks like. If the user only wants the trend chart with no
eligibility/score context, prefer `stock-financials-chart` instead — it's a leaner output
for that narrower ask. Works for any ticker in either index, current holding or not; the
only requirement is a cache file at `cache/stocks_data/{TICKER}_US.json` or `_TA.json`.

## How to run it

```bash
python3 .claude/skills/stock-snapshot/scripts/generate_snapshot.py <TICKER> --output <path>.html
```

- `<TICKER>` — same resolution rules as the chart skill (bare ticker auto-resolves `_US.json`
  then `_TA.json`; pass the suffix explicitly, e.g. `MTRX_TA`, if needed).
- `--output` — always pass an explicit path into the current scratchpad directory.
- Exits 1 with a clear message if no cache file matches, if the file has no usable financial
  data, or if the cache file can't be loaded as a `Stock` model — surface that message rather
  than retrying blindly.

Then publish the output file with the Artifact tool directly — do **not** reload `dataviz` or
`artifact-design` for this; the template already encodes their rules. Use:
- `title`: `"<TICKER> Fund Snapshot"`
- `description`: one sentence naming eligibility, score, and the metrics charted
- `favicon`: `📋`

## What the script does

1. Resolves the ticker to a cache file and loads it two ways: `build_chart_data` (from the
   sibling `stock-financials-chart` skill) for the chart, and `utils.cache_loader.load_cached_stock`
   for a full `Stock` model to run eligibility checks against.
2. **Eligibility is recomputed live**, not read from the cache's stored flag —
   `Stock.check_base_eligibility()` / `check_potential_eligibility()` are pure and
   deterministic, so calling them fresh is both cheap and more trustworthy than a boolean
   that may be stale relative to the current eligibility rules. The stored flag is compared
   against the recomputed result; a mismatch is shown as a note (it means eligibility rules
   or the cached figures changed since this ticker's cache was last written), not silently
   overwritten.
3. Each eligibility axis gets a full per-criterion breakdown table (6 rows for Base, 2 for
   Potential), computed by re-deriving each check directly from the same fields the real
   methods use (`net_incomes`, `operating_incomes`, `operating_cash_flows`, `total_equity`,
   `debt_to_equity_ratio`) — so the breakdown can't drift from what actually gates
   eligibility. Where the real check treats missing equity/debt data as a silent non-failure,
   the breakdown shows that explicitly as **N/A**, not a false PASS.
4. `base_score`/`potential_score` are shown independently, each gated on its own cache field
   being non-null (a stock can have both, one, or neither). When populated, the breakdown
   table uses the real `base_scores_detail`/`potential_scores_detail` keys and the live
   weight constants from `config.settings` (never hardcoded copies), with a formula-recap
   total row that re-derives the score from its own stored sub-values — this doubles as a
   free staleness check if it ever diverges from the stored score. Every populated score
   block is captioned as **percentiles within the candidate pool as of the last full build or
   quarterly update** — unlike eligibility, scores are not recomputed live (that would require
   the full candidate pool, not just this one ticker's cache file). When a score is null, a
   muted line says so instead of silently omitting the section.
5. Composes the Fund Status card with the chart skill's `render_chart_card_markup()` /
   `render_chart_scripts()` under one shared `<style>` block and one `<title>` — not two
   separate documents glued together, which would duplicate ids/styles.

## Known limits

- Single ticker per snapshot — no side-by-side ticker comparisons.
- Scores/ranks are as-of-last-build, never live-recomputed (see point 4 above).
- Eligibility is recomputed live but only as fresh as the cached fundamentals themselves —
  it can't be more current than the last time this ticker's cache file was written.
- This skill imports `resolve_cache_file`, `build_chart_data`, `render_chart_card_markup`,
  `render_chart_scripts`, and the shared CSS constants directly from
  `stock-financials-chart/scripts/generate_chart.py`. If that file's function names or
  signatures change, this skill breaks — that coupling is intentional (real reuse, not
  duplicated chart logic) but worth knowing when editing either skill.
