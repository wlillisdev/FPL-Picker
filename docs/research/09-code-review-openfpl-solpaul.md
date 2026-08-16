# Code Review: OpenFPL & solpaul/fpl-prediction

*2026-08-15. Direct inspection of two open-source FPL prediction codebases (both MIT licensed —
freely reusable with attribution). Verdict up front: **OpenFPL ships pre-trained models we can
run directly as our Phase 2 forecaster**, and solpaul's repo is the blueprint for our Phase 4
backtest harness. Neither needs reinventing — we integrate and then beat them where they're weak.*

## OpenFPL (github.com/daniegr/OpenFPL) — the big prize

### What it actually ships
- **724MB of pre-trained XGBoost ensembles**: 5 cross-validation folds × 5 positions
  (GK/DEF/MID/FWD/AM), each folder holding the top candidates from a K-Best hyperparameter
  search, as plain `joblib` files. Plus the fitted feature scalers and per-position feature
  lists. `play.ipynb` shows the complete inference recipe in ~40 lines.
- **The exact feature recipe** (`data/samples.csv`, 235 columns):
  - Player stats × rolling windows of last **{1, 3, 5, 10, 38} matches**: FPL points,
    "relevant" FPL points, minutes, influence/creativity/threat, goals, assists, goals
    conceded, own goals, saves, penalties saved/missed, cards, BPS, bonus — plus Understat:
    **shots, xG, xGChain, xGBuildup, key passes, xA**.
  - Team stats × same windows: goals for/against, league rank, opponent league rank, team
    xG/xGA, **deep completions and PPDA** (territory and pressing intensity, from Understat).
  - Context: home flag, opponent.
- **Inference**: scale features (NaN→0, standard scaler) → per-position feature subset →
  predict with every ensemble member (~25+ models per position across folds) → **median**.
- **Honest head-to-head vs FPL Review** (from their README): OpenFPL wins on "Tickers"
  (3-4 pt games, RMSE 1.517 vs 1.594) and "Haulers" (≥5 pts, 5.142 vs 5.172) — the
  categories that decide rank — and loses on "Zeros" and "Blanks" (0.818 vs 0.689), i.e.
  FPL Review's proprietary minutes model is better at knowing who won't play.

### Integration path for FPL-Picker (Phase 2)
1. Build a **samples builder**: FPL API (`bootstrap-static` + `element-summary`) + Understat →
   235-column rows per player-fixture, matching `samples.csv` exactly. This is the only real
   work — mostly rolling-window bookkeeping plus FPL↔Understat ID mapping.
2. Load their scalers/models via joblib and predict; median-ensemble. One row per future
   fixture (opponent + home flag per row) gives us per-GW projections over any horizon.
3. Keep our current blend as fallback when models/Understat data are unavailable.

### Where we beat it (the "do it better")
- **DefCon blindness**: trained through 2023-24 — it has never seen defensive-contribution
  points (2025/26) and doesn't know the 2026/27 BPS changes. Fix: add our own DefCon layer
  (prior-season CBIT/tackle rates predict it almost deterministically — see case study) on
  top of OpenFPL's output, and a bonus adjustment for the CBI nerf.
- **The minutes gap is quantified** (their Zeros/Blanks loss): gate their predictions with
  our own P(start)/P(60') model + the overrides file. Their own paper names this the open
  frontier.
- **Staleness risk**: models are frozen at 2024-25; they'll drift as the game changes.
  Mid-term we retrain on vaastav data (their framework is reproducible — K-Best Search is
  also on GitHub) with DefCon-era targets.

## solpaul/fpl-prediction — the methods quarry

- **The validation blueprint we should copy for Phase 4**: for each GW of a held-out season,
  refit on all history *prior* to that week, then score MAE over the **next 6 gameweeks**;
  chart performance across the season. That's a proper walk-forward harness, exactly what
  our audit says we lack.
- **Reference implementations** in `fpl_predictor/util.py` (513 lines): `player_lag_features`
  / `team_lag_features` (rolling-window generation), `create_lag_train` (train/valid
  splitting by season+GW) — directly adaptable.
- **307MB of cleaned historical data** (2016-17 → 2022-23, built on vaastav) — a bootstrap
  for our historical store, though it stops at 2022-23.
- **Their model comparison** (validated GW-by-GW on 2020/21): LSTM edged XGBoost, random
  forest, and a fastai tabular net. Notably they used **no Understat features** — OpenFPL's
  result suggests feature quality (xG data) mattered more than the LSTM's sequence modeling.
  Conclusion for us: don't chase deep nets; chase features.
- Repo is stale (last data 2022-23) — use as reference, not dependency.

## Actions taken / planned

- Blueprint Phase 2 updated: OpenFPL integration is now the named path for projection v1
  (decomposition model remains the complement for minutes/DefCon/CS where OpenFPL is weak).
- Phase 4 backtest harness spec: adopt solpaul's refit-each-GW / MAE-over-next-6 design.
- Both repos cloned read-only and inspected; nothing vendored yet — models would be fetched
  at install time or documented as an optional download (724MB doesn't belong in our git).
