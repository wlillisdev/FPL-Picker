# Cold-Start Forecasting: How the Reference Systems Handle GW1-6

*2026-09. Research commissioned after our GW1-2 selection failures. Grades our fixes against
best practice and sets the corrections. Key calibration fact: a PERFECT model scores RMSE
2.81 / R² 0.15 on single-GW points — GW1-2 burns are ~85% irreducible variance.*

## What the reference systems do

- **FPL Review**: never waits for current-season data — its player model gates on **450
  career/background minutes**, uses bookmaker odds for team strength (odds price in news
  faster than any stat), refreshes xMins hourly, and treats manual xMins overrides as a
  feature. **OpenFPL**: solves cold start architecturally — every feature computed over
  1/3/5/10/38-match windows *spanning seasons*, letting the model weight short vs long.
- **Timelines**: team-level signal (xGD) becomes significant ~4 games; player per-90 signal
  needs 8-12 matches; current-season-only models reach parity with priors at matchday 10-25.
- **Form is near-worthless**: five-season studies find week-to-week form has essentially no
  predictive value; fixtures do (especially for expensive mids). Finishing (G−xG) regresses
  ~fully to zero at any early-season sample.
- **The GW1 accuracy spread between commercial sites is dominated by minutes prediction**,
  not scoring models (FPL Watchmen site comparison).

## Corrections to our fixes (status)

| Our fix | Verdict | Correction | Status |
|---|---|---|---|
| Form shrink n/(n+4) | Right idea, 2-3x too trusting | **k=10** for output rates; role/minutes signals should dominate from match 1 (already true via participation factor) | ✅ shipped |
| Price prior 0.32p+0.7 | Right idea, wrong form | Anchor to **GW1 price** (now_cost − cost_change_start); **concave** slope flattening above £9.0m; position-specific curves later | ✅ shipped (positional curves TODO) |
| OpenFPL gate at 4 current-season matches | Wrong gate | Gate on **~450 career minutes** and build features spanning seasons (needs last-season per-match data — FPL-Core-Insights ingest) | 🔜 queued (the GW1-6 dead-zone killer) |
| Participation (n+1)/(G+1) | Placeholder | Real xMins: p(start)·E[min|start] + p(cameo)·E[min|cameo]; aggregate 2-3 predicted-lineup sources (FFScout Team News, fpl.team, SportsGambler); ~0.8× penalty first days post-transfer; congestion flags | 🔜 queued |
| Hold-unless-structural advice | Matches best practice | Act on 2-match samples only for minutes/role/penalty evidence, never output | ✅ encoded |

## Other adopted priors

- **Promoted teams**: recent cohort brutal — six straight-relegations, none over 26 points.
  Set CS/attack priors at the relegated-cohort level, discount Championship per-90s hard.
- **Team strength GW1-6**: odds-implied ratings essentially solve the team cold start; free
  fallback = cross-season Dixon-Coles with ξ≈0.0019/day (half-life ~1 year — at GW3 a match
  from last March still deserves ~70% weight), promoted teams initialized at relegated-team
  ratings.
- **New signings**: league-strength discount, wide variance, fast Bayesian update; FPL price
  already encodes expert judgment — the price prior carries most weight exactly here.
- **Evaluation**: prefer rank-correlation / top-N hit rate / minutes error over raw MAE
  (our 600-player MAE is flattered by benchwarmers).

Full citations in the research transcript; headline sources: FPL Review MDM/xMins docs,
OpenFPL (arXiv 2508.09992), FPL Watchmen GW1 comparison, Dixon-Coles time-weighting
literature, Mathematically Safe five-season study, The Analyst promoted-team data.
