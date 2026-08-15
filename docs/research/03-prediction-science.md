# Research: What Actually Predicts FPL Points

*Compiled 2026-08-15 from web research (agent report). Informs the FPL-Picker prediction model.*

## (a) Anatomy of a state-of-the-art xPts model

### The canonical decomposition
Every respected model (FPL Review, FPLForm, Fantasy Football Fix xFPL, Tokvam's Transfer Algo)
is built on the same probabilistic decomposition
([FPL Copilot explainer](https://fplcopilot.com/blog/expected-points-explained),
[Fix xFPL docs](https://support.fantasyfootballfix.com/support/solutions/articles/202000055995-what-is-expected-fpl-points-xfpl-),
[Leadboot's open modelling series](https://medium.com/@marcusleadboot/modelling-xpts-in-fpl-gameweek-1-01fd2179eac6)):

```
E[pts] = P(plays 1+ min) × 1  +  P(plays 60+ min) × 1            (appearance)
       + E[goals | plays] × goal_pts(position)                    (opponent-adjusted xG + penalty share)
       + E[assists | plays] × 3                                   (opponent-adjusted xA)
       + P(clean sheet) × P(plays 60+) × CS_pts(position)         (team-level model)
       + E[bonus]                                                 (BPS model)
       + E[saves]/3 × 1 + E[goals conceded]/2 × (−1)              (GK/DEF)
       + E[cards] × (−1) + defensive-contribution pts             (2025/26+ rules)
```

Key refinements:
- **Opponent adjustment**: per-90 xG/xA must be scaled by opponent strength — fixture difficulty
  is "the variable most models underweight".
- **Penalties**: a penalty ≈ 0.79 xG, worth 2–3 extra points per team penalty; track takers
  explicitly.
- **Simulation rather than closed-form**: FPL Review runs 1,000 per-player match sims per GW —
  correctly captures interactions (CS needs 60+ min; bonus correlates with goals).

### State of the art
- **FPL Review Massive Data Model**: statistics + ML over historical performance, market odds,
  team strength/style, roles, penalty/rotation status, recency; projects to 14 GWs. Its
  goalscoring sub-model **beats de-margined bookmaker anytime-scorer odds** (which carry ~45%
  margins) ([article](https://docs.fplreview.com/articles/massive-data/)).
- **OpenFPL** ([arXiv 2508.09992](https://arxiv.org/abs/2508.09992)): position-specific
  ensembles of 50 models regressing points **directly** (no decomposition), FPL API + Understat,
  forecast = ensemble median. Prospectively non-inferior to FPL Review, up to **5% better on
  high-return (>2 pt) players**. Both beat naive baselines by 5–34% RMSE.
- **FPL Pulse** (GBM on 5 seasons): **0.81 MAE vs 1.05 for FPL's official xP** on 15,572
  held-out player-fixtures ([model page](https://www.fplpulse.com/blog/fpl-predicted-points-model)).
- **FPLForm** publishes xPts both **conditional on appearing** and with a separate
  **probability-of-appearing** — the right interface for a solver
  ([predictions](https://fplform.com/fpl-predictions)).

### The accuracy ceiling — calibrate expectations
FPL Review's ["Ultimate Truth" study](https://docs.fplreview.com/articles/ultimate-truth/): a
**perfect** model (knowing true probabilities) achieves only **RMSE ≈ 2.81, MAE ≈ 1.96,
R² ≈ 0.146** on single-GW points. FPL is dominated by irreducible variance. Judge models on
calibration and ranking of high-return players, not raw R².

## (b) Minutes prediction — the hardest, highest-leverage component

1. **Simulation-based xMins (FPL Review)**: the critical split is **P(start), P(sub appearance),
   E[min|start], E[min|sub]** — 60+ minutes gates the second appearance point and CS points
   ([xMins docs](https://docs.fplreview.com/the-model/projections/xmins/)).
2. **Starts-based statistical models**: recent-starts share, minutes distribution, FPL API
   availability flags (25/50/75% chance), team depth.
3. **Human/news curation**: predicted line-ups updated after Friday press conferences
   ([FFS Team News](https://www.fantasyfootballscout.co.uk/team-news)). Community consensus:
   early-season and around news, **"a qualitative assessment by an attentive fan is almost
   certain to trump anything statistical"** ([AlpsCode](https://alpscode.com/blog/intro-to-fpl-analytics/)).
   Design for human-in-the-loop overrides.
4. **NLP on news**: transformer sentiment on football news improved predictions in a 2025
   academic effort — promising, not yet standard.

Why it dominates: xPts scale almost linearly with minutes — a 60%-starter with 6.0
xPts-if-playing is a 3.6 xPts asset. Errors in P(start) dwarf errors in per-90 rates.

## (c) Feature ranking — what earns its keep

1. **Minutes/availability signals** (largest error component).
2. **Opponent-adjusted xG/xA, not actual goals** — xG predicts future goals better than past
   goals, especially in small samples.
3. **Shot volume and big chances** — stabilize faster than conversion.
4. **Finishing skill (G − xG): mostly noise.** Regress ~fully to zero for almost everyone; use
   npxG + penalty share ([KU Leuven](https://dtai.cs.kuleuven.be/sports/blog/biases-in-expected-goals-models-confound-finishing-ability/)).
5. **Team-level xG for/against** — drives CS and goals-conceded expectations.
6. **Penalty/set-piece duty** — discrete, high-value, hand-maintained.
7. **Bookmaker odds** — team-level signal that prices in news faster than stats sites.
8. **Recent form of actual FPL points** — weak once xG/xA/minutes are in the model.

## (d) Odds vs FPL's FDR

- Official FDR: single 1–5 ordinal scale, doesn't separate attacking vs defensive difficulty,
  ignores news, static.
- Best practice: **de-margin bookmaker 1X2 + over/under 2.5 lines → implied team xG for/against →
  Poisson → clean-sheet probabilities** ([Fantasy Football Geek](https://www.fantasyfootballgeek.co.uk/using-betting-odds-in-fpl/)).
- Use match-level odds as team inputs; don't lean on anytime-scorer odds (huge margins).
- Odds are a floor, not a ceiling (FPL Review's own model narrowly beats them).

## (e) Simple vs ML findings

- Uppsala thesis (2025): **linear regression and XGBoost performed similarly** in a GW1–21
  simulation — feature quality beats model class in this low-signal domain.
- OpenFPL: well-tuned GBM ensembles with good features **match** the commercial state of the
  art; direct regression and decomposition reach the same ceiling.
- Deep learning (LSTM/transformers): no evidence of beating a good GBM/decomposition; datasets
  too small.
- AIrsenal's elegant Bayesian team model had famously mixed real-world results.
- **Most achievable gain comes from minutes accuracy, opponent adjustment, and odds ingestion —
  not model complexity.**

## (f) Horizon and decay

- FPL Review projects to 14 GWs; solver users typically run 5–14.
- **Exponential decay, default 0.84/GW** (community standard; range 0.80–0.95; lower when
  chasing rank, higher for long-term planning).

## (g) Recommended model design for FPL-Picker

**Probabilistic decomposition first, ML residual layer optional later.**

1. **Minutes module (build this best):** per player output {P(start), P(sub), E[min|start],
   E[min|sub]} → P(≥1 min), P(≥60 min). Inputs: rolling starts share (recency-weighted),
   FPL status/chance flags, days-since-injury-return, fixture congestion, plus a **manual
   override layer** from predicted line-ups/news.
2. **Team module:** de-margined bookmaker odds → implied team xG for/against per fixture;
   Poisson → P(CS), E[goals conceded]. Fall back to Elo/Dixon-Coles blend when odds unavailable.
   Never use official FDR except as UI garnish.
3. **Player attack module:** per-90 npxG and xA (multi-season, recency-weighted; shrink G−xG to
   ~0), scaled by opponent implied xGA / league average and home/away. Add penalty-taker
   expected pens × 0.79 xG.
4. **Bonus + sundries:** empirical E[bonus | goal/assist/CS, position] + baseline per-90 BPS;
   GK saves via Poisson on opponent shot volume; cards; defensive-contribution points from
   CBIT/tackle rates.
5. **Assembly by simulation:** ~1k Monte-Carlo sims per player-match; report mean xPts plus
   **P(return > 4 pts)** — the tail decides rank.
6. **Horizon & decay:** 8 GWs (odds-based GW+1..2, model-based beyond); decay default 0.84.
7. **Validation:** walk-forward backtests per position and per return-category vs naive-form
   baseline and FPL's official xP; remember the perfect-model ceiling (RMSE ~2.8, R² ~0.15).
8. **Later:** optional LightGBM residual/direct layer per position — expect single-digit-% gains
   at most over a well-built decomposition.
