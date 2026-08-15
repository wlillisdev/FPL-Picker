# Research: Open-Source FPL Tools & Systems

*Compiled 2026-08-15 from web research (agent report). Informs the FPL-Picker architecture.*

## (a) Notable systems

### 1. sertalpbilal's FPL-Optimization-Tools ("the open-source solver")
- The de-facto standard open-source FPL solver, used by many top-1k managers. Takes an
  expected-points (EV) projection CSV as input and solves squad selection, lineup, captaincy,
  transfers, and chip timing as a deterministic optimization problem
  ([repo](https://github.com/sertalpbilal/FPL-Optimization-Tools), [Solio](https://solioanalytics.com/)).
- Python + pandas, MILP via sasoptpy, solved with the open-source **HiGHS** solver. Covers
  single-period EV maximization and **multi-period EV maximization over an N-gameweek horizon**,
  wildcard/chip optimization, configurable constraints (formations, banned/locked players,
  transfer logic, hit costs). It deliberately does **not** produce projections — you bring your
  own. Companion assets: "Let's Solve FPL" YouTube series (including fixing subtle logic errors
  like multiple-sell events in wildcard weeks — [episode](https://www.youtube.com/watch?v=4PNcDUoRQOE)),
  a Colab notebook, the [fpl_optimized](https://github.com/sertalpbilal/fpl_optimized) site,
  and the [FPL Optimized podcast](https://fploptimized.transistor.fm/episodes).
- **Takeaway:** separate projections from optimization behind a clean CSV/dataframe interface;
  formulate transfers/chips as one multi-period MILP; use HiGHS (free, fast enough). This
  separation is why the tool outlived its original projection source.

### 2. FPL Review (commercial, hugely influential)
- The reference expected-points provider + hosted planner/solver
  ([site](https://fplreview.com/), [docs](https://docs.fplreview.com/getting-started/about-fplreview/)).
  Its "Massive Data Model" projects every scoring event weighted by probability out to ~14
  gameweeks, and runs **1,000 per-player match simulations per gameweek**
  ([MDM docs](https://docs.fplreview.com/the-model/projections/massive-data-model/)). Publishes a
  goalscoring model claimed more predictive than bookmaker-implied odds
  ([article](https://docs.fplreview.com/articles/massive-data/)) and the "Ultimate Truth"
  benchmark vs a hindsight-perfect model
  ([article](https://fplreview.com/ultimate-truth-how-fpl-models-perform-relative-to-a-perfect-model/)).
- Went through a period of uncertainty and is **live again for 2026/27** — its wobble is what
  spawned OpenFPL and community EV sheets. Don't hard-depend on any one projection vendor.
- Approach: statistical + ML hybrid over historical performance, **market odds**, team
  strength/style, player roles, penalty-taker status, rotation risk, recency weighting, and
  **proprietary expected-minutes projections**. Its solver docs define the standard planning
  vocabulary: **time decay**, **free-transfer value**, **bank value**, **sensitivity analysis**
  ([sensitivity docs](https://docs.fplreview.com/the-model/solvers/sensitivity-analysis/),
  [settings](https://docs.fplreview.com/the-model/solvers/settings/),
  [glossary PDF](https://fplreview.com/wp-content/uploads/Solver-Glossary.pdf)).
- **Takeaway:** the EV model is the moat; expected minutes + odds integration are its two biggest
  ingredients. The solver-side concepts are all reimplementable.

### 3. OpenFPL (daniegr, 2025 paper)
- Open-source forecasting method "rivaling state-of-the-art FPL services"
  ([arXiv 2508.09992](https://arxiv.org/abs/2508.09992), [repo](https://github.com/daniegr/OpenFPL)).
- One **ensemble regressor per position** (XGBoost + Random Forest), trained on **public data
  only** (FPL API + Understat, 2020-21 → 2023-24), evaluated **prospectively** on 2024-25.
  Comparable accuracy to FPL Review's Massive Data Model overall and **better on high-return
  players**. Skips expected-minutes modeling (uses only FPL API availability flags) and still
  competes; flags minutes forecasting as the open frontier.
- **Takeaway:** position-specific gradient-boosted ensembles on FPL+Understat data are a proven,
  reproducible baseline; walk-forward evaluation against a commercial benchmark is the right
  validation design.

### 4. AIrsenal (Alan Turing Institute)
- End-to-end "AI FPL manager" since 2018/19: data ingestion → Bayesian prediction →
  transfer/chip optimization → optional API submission
  ([repo](https://github.com/alan-turing-institute/AIrsenal),
  [Turing page](https://www.turing.ac.uk/news/airsenal)).
- Two-stage probabilistic model: team-level Dixon-Coles-style scoreline model + player-level
  goal-involvement model conditioned on the scoreline; jax/numpyro Bayesian inference; genetic
  algorithms in the search stack.
- **Takeaway:** principled generative models are interpretable and data-efficient, but AIrsenal
  has historically underperformed the projections+MILP stack; its value to us is the pipeline
  shape (DB → ingest → predict → optimize → apply) and its documented failure modes.

### 5. vaastav/Fantasy-Premier-League (historical dataset) — and successors
- Canonical season-by-season FPL archive from **2016-17**: per-gameweek CSVs per player, merged
  gameweek files, Understat xG/xA merges, full data dictionary
  ([repo](https://github.com/vaastav/Fantasy-Premier-League)). Nearly every FPL ML paper trains on it.
- **Weekly updates discontinued after 2024-25.** Successors: **FPL-Core-Insights /
  FPL-Elo-Insights** (official API fused with match stats + dynamic team Elo, keyed to official
  FPL IDs, through 2026/27 — [repo](https://github.com/olbauday/FPL-Core-Insights)) and
  [FPLYogi/FPL-Data](https://github.com/FPLYogi/FPL-Data).
- **Takeaway:** train on vaastav (2016-25); run our own live collector going forward. The
  "everything joined on official FPL element IDs" design is the right pattern — ID mapping
  between FPL/Understat/FBref is a notorious chore.

### 6. Smaller but instructive
- [amosbastian/fpl](https://github.com/amosbastian/fpl) — async Python FPL API wrapper.
- [LazyFPL](https://github.com/janbjorge/lazyFPL), [open-fpl](https://github.com/bapairaew/open-fpl),
  [JFPL-Optimization](https://github.com/TDRoss/JFPL-Optimization) (Julia port of the solver).
- [penaltyblog](https://pypi.org/project/penaltyblog/) — Dixon-Coles-family goal models plus
  scrapers (football-data, FBref, Club Elo, Understat, FPL) — building blocks for team strength.
- Academic: Ramezani & Dinh ([arXiv 2505.02170](https://arxiv.org/abs/2505.02170)) —
  deterministic and **robust** MILPs; ARIMA + rolling window most consistent out-of-sample.
- Benchmark/feature comparators: Fantasy Football Fix, Fantasy Football Hub,
  [FPLForm free predicted points](https://fplform.com/fpl-predicted-points),
  [FPL Watchmen accuracy comparisons](https://fplwatchmen.substack.com/p/fpl-2025-gw1-analysis-of-prediction).

## (b) Optimization techniques worth adopting

1. **Multi-period MILP as the core** — squad/lineup/captain/bench-order/transfers per GW over an
   N-week horizon (5–8 typical), with budget, 3-per-club, formation, transfer-carryover constraints.
2. **Exponential time decay** on future-GW EV (~0.84/GW community default; range 0.80–0.95).
3. **Terminal-value terms**: EV for carried free transfers (~1.5 pts heuristic) and bank money,
   so the solver doesn't burn flexibility for marginal immediate gains.
4. **Sensitivity analysis / re-solve ensembles**: many solves under coherently perturbed inputs;
   report how often each move appears in the optimal plan.
5. **Chips inside the same model** — binary per-week activation variables with their special
   rules, solved jointly (watch the multiple-sell-events trap in wildcard weeks).
6. **Hits as priced variables** — -4s allowed but charged in the objective.
7. **Simulation on top of point estimates** — scenario sampling or robust constraints for
   captaincy/rank-sensitive decisions.
8. **Solver: HiGHS** (open source) is sufficient.

## (c) Data sources ranked by value

1. **Official FPL API** (free, no auth for reads): `bootstrap-static/`, `fixtures/`,
   `element-summary/{id}/`; authenticated endpoints for your own team
   ([endpoint guide](https://medium.com/@frenzelts/fantasy-premier-league-api-endpoints-a-detailed-guide-acbd5598eb19),
   [Oliver Looney's writeup](https://www.oliverlooney.com/blogs/FPL-APIs-Explained)).
   **Snapshot it weekly ourselves.**
2. **vaastav historical dataset** (2016-17 → 2024-25) + **FPL-Core-Insights** for current seasons.
3. **Understat xG/xA** — highest-value external signal per unit of effort; the only external
   source OpenFPL needed to match a commercial model.
4. **Bookmaker odds** (match result, clean sheet) — efficient prior for team-level inputs; free
   alternative is a Dixon-Coles/Elo team-strength model.
5. **FBref** — richer per-player stats (defensive actions matter since the 2025/26
   defensive-contribution points); heavier scraping burden.
6. **Team news / press-conference minutes intel** — no good structured source; the gap everyone
   works around.

## (d) Pitfalls and lessons reported by authors

1. **Minutes prediction is the hardest, highest-leverage problem.** Design the EV model as
   P(minutes bands) × points-given-minutes from day one.
2. **Stale priors kill early-season performance.** AIrsenal's "difficult second season": stacked
   Chelsea defenders off historical strength while Chelsea conceded in six straight
   ([Turing blog](https://www.turing.ac.uk/news/airsenal-difficult-second-season)). Recency-weight
   and shrink historical priors fast; consider odds/Elo as dynamic team strength.
3. **Pipeline rot masks model failures** — API-dependent tests silently broke in AIrsenal. Need
   API-independent fixtures and per-GW data validation.
4. **Projections >> solver (garbage in, garbage out).** The solver is a commodity; chase EV-model
   quality. Even a hindsight-perfect model captures only part of achievable points.
5. **Single-week greedy planning is a known trap** — multi-week horizons with decay + FT/bank value.
6. **Point estimates hide fragility** — report "optimal in 78% of perturbed solves", not one plan.
7. **Evaluate prospectively and position-wise**, specifically on high-return players — average
   RMSE is dominated by benchwarmers.
8. **Dependency risk is real** — datasets stop updating, vendors go dark, FPL changes rules
   yearly (2025/26 defensive-contribution points; 2026/27 live scoring). Own the data collection,
   keep scoring rules config-driven, keep the projections↔solver interface vendor-neutral.

**Bottom-line architecture implication:** the community-converged reference design is:
(1) own FPL-API snapshot collector + historical store keyed on FPL IDs; (2) position-specific ML
EV model on FPL+Understat features with an explicit minutes submodel; (3) multi-period MILP with
decay, FT/bank value, chips, hits; (4) sensitivity/simulation wrapper; (5) prospective
per-position evaluation against public benchmarks.
