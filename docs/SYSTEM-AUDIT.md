# FPL-Picker System Audit

## v0.3 — Two weeks live (2026-09, after GW1-2 in production)

The first audit below was written before contact with reality. This section is
the retrospective after two live gameweeks. Verdict up front: **the ranking
layer is provably good, the selection layer shipped over-trusting and needed
three emergency fixes, and the biggest unexploited asset is last-season data
we still don't use.**

### What the live evidence proved GOOD
- **Ranking accuracy (the measured thing):** beat the price-only baseline in
  both scored gameweeks (MAE 1.79 vs 2.25; 1.49 vs 2.13), and GW2's top-10
  rated players went **10/10 for returns** (incl. rating Palmer and Saka
  top-5 *before* their hauls). The core signal works.
- **The discipline layer:** refused hits below threshold, recommended holds,
  banked FTs — every strategy-rule behavior fired correctly.
- **The audit loop itself:** every user-visible failure produced a same-day
  fix with a regression test (6 fixes, 43 tests). Failures don't recur.

### What the live evidence proved BAD
1. **Selection-layer defaults trusted tiny samples.** Three absurd outputs
   reached the user before guardrails existed: a one-match DefCon haul
   captained (Egan), a one-match blend haul captained (Stach), an
   unused player started (Davies). Root cause each time: n=1-2 data treated
   as track record. Now gated — but these should have been anticipated; the
   research *said* early weeks were the worst regime.
2. **No last-season data in the live path.** The cold-start anchor is price
   alone; prior-season per-90s (sitting unused in our cloned datasets) are a
   strictly better prior. This is the biggest known accuracy giveaway.
3. **Minutes remains the #1 error source** — the participation heuristic is
   a patch, not a model. Predicted-lineup ingestion is still missing.
4. **Understat integration has produced zero value so far** (site lags the
   season; features blank). The xG half of the feature space is dark.
5. **The rate-my-team score is volatile** (61 → 90 → 77 across fixes)
   because the "perfect wildcard" comparator inherits every scoring-layer
   bias. It should be presented with error bars or a stability caveat.
6. **Vice-captain/EO logic is crude** (ownership proxy, no real captaincy
   shares; vice picked by raw metric).

### Priority queue (informed by the elite-teams and cold-start research runs)
1. Blend last-season per-90/per-GW data into early-season scores with a
   crossover schedule (expected biggest accuracy jump; datasets on hand).
2. Predicted-lineup/minutes ingestion (manual override file exists; needs a
   data source).
3. Wildcard planning support for the GW4-8 window (multi-period spec ready).
4. Rating stability: report score ranges, not point estimates.
5. Elite-EO tracking (top-10k ownership) once sources are identified.

---

# Original audit (v0.2, post-Phase 1, pre-season)

*2026-08-15. An honest internal SWOT of our own system — what's solid, what's weak, and the
prioritized plan to make it better. Complements the market-facing SWOT in
[`docs/research/04-competitive-landscape-swot.md`](research/04-competitive-landscape-swot.md).*

## Strengths (what's genuinely solid)

1. **Constraint handling is provably correct.** Budget, squad shape, club limits, formations,
   captaincy — all enforced by the MILP and covered by tests. The optimizer layer is
   trustworthy; whatever scores go in, the squad that comes out is legal and optimal for them.
2. **The transfer solver has real strategy discipline built in.** Hits priced at 4 points and
   only recommended past the researched threshold (>4 + margin over the horizon); "hold your
   transfers" is a first-class recommendation, which most tools won't say.
3. **Snapshot mode decouples us from network fragility** — a design decision that already paid
   off when the FPL API turned out to block cloud hosts.
4. **Fully offline test suite (16 tests)** — no API dependency, so tests can't rot the way
   AIrsenal's did.
5. **A documented evidence base.** Six research docs tie every design decision to sources.
   Few tools of any size can show *why* their rules exist.

## Weaknesses (ranked by how much they cost us in points)

1. **The scoring model degenerates at exactly the wrong time.** At GW1, form/PPG/xGI are all
   empty, so scores collapse to FPL's black-box `ep_next` scaled by fixtures. We are currently
   a re-ranking of FPL's own opinions. Even mid-season, blending `ep_next` with form/PPG
   double-counts correlated information rather than adding independent signal.
2. **No minutes model.** The research is unambiguous that P(start)/P(60') errors dominate all
   other errors. We only zero-out injured players and scale doubtful ones.
3. **Blind to role and team news.** The strongest pre-season signals (Mbeumo moving to
   striker, Szoboszlai moving deeper) are invisible to the model, and until now there was no
   way to inject that knowledge except crude lock/exclude.
4. **No clean-sheet, save, bonus, or defensive-contribution modeling.** Goalkeepers and
   defenders are ranked almost entirely by `ep_next` — the "why is it picking a Palace
   keeper" problem. DefCon was the single biggest exploitable edge of 2025/26 and we don't
   model it at all.
5. **Fixture adjustment uses the official FDR** — the research verdict was "never use official
   FDR except as UI garnish"; odds-implied or Elo-based difficulty is materially better.
6. **Captaincy = highest mean score.** The evidence says captaincy should weight P(haul)
   (doubling amplifies the tail), venue, opponent, penalty duty, and effective ownership.
7. **No ownership/EO awareness anywhere.** The optimizer maximizes raw points; rank is
   relative to the field. Two squads with equal xPts can have wildly different rank outcomes.
8. **Transfer planning is single-week.** No multi-GW sequencing, no free-transfer banking
   value, no chip planning. Sell prices are approximated by current price (the public API
   hides purchase prices), which drifts wrong as prices change.
9. **Point estimates with no uncertainty.** A +7.5 recommendation and a +2.1 recommendation
   print with equal confidence; the noise floor says they shouldn't.
10. **We don't measure ourselves.** No record of what we predicted, so no way to learn what
    our actual error looks like. Unvalidated weights (0.35/0.25/0.25/0.15) chosen by judgment.

## Opportunities (the improvement plan, prioritized by impact/effort)

| # | Improvement | Impact | Effort | Status |
|---|---|---|---|---|
| 1 | **Manual override layer** — score multipliers from a JSON file, so scouting intel (role changes, soft injury news) feeds the model today | High | Low | **Shipped with this audit** |
| 2 | **Prediction logging** — save every run's projections keyed by GW, so from GW1 we accumulate our own accuracy record | High (compounding) | Low | Next |
| 3 | **Phase 2 decomposition model** — minutes module, team strength (Elo/Dixon-Coles, not FDR), opponent-adjusted npxG/xA, penalty duty, DefCon floor, CS/save/bonus sub-models | Very high | High | Designed (blueprint) |
| 4 | **Captaincy algorithm** — P(haul)-weighted, venue/opponent-aware, EO-aware by rank state | High | Medium | Research in flight |
| 5 | **EO-aware optimization** — ownership data is already in the API; add a rank-variance term to the objective | High | Medium | After 4 |
| 6 | **Backtest harness** on historical seasons (vaastav data) to calibrate weights and publish honest accuracy | High | High | Phase 4 |
| 7 | **Multi-GW transfer sequencing + chips** — decision variables per week, FT banking value, chip windows | Medium-high | High | Phase 3 |
| 8 | **Sensitivity wrapper** — re-solve under perturbed scores, report "recommended in N% of solves" | Medium | Medium | Phase 4 |
| 9 | Understat xG + odds/Elo ingestion | Enables 3 | Medium | Phase 2 |
| 10 | CI (GitHub Actions running the test suite), fix PuLP deprecations | Hygiene | Low | Anytime |

## Threats (what could invalidate our work)

- **FPL API drift** — unversioned; any field rename breaks ingestion silently. Mitigation:
  data validation on fetch, snapshot regression fixtures.
- **Overfitting to last season's meta.** DefCon was 2025/26's edge, but 2026/27 tweaks BPS to
  reduce DefCon overlap — the edge may already be partially repriced. Rule constants must stay
  config-driven and be revisited each season.
- **Confidence outrunning validation.** Until the backtest harness exists, every score the
  system prints is an unvalidated estimate; recommendations should stay humble (and the
  uncertainty work in #8 makes that structural).
- **Sell-price drift** — our transfer budgets get slightly wrong as prices change; needs
  purchase-price tracking (user-supplied or persisted from GW1).
- **Single-maintainer bus factor** and free-tier hosting limits (documented in the blueprint).

## The one-sentence verdict

The optimizer is the trustworthy half of the system and the scoring model is the weak half —
so every point of effort should go into signal quality (overrides now, decomposition model
next, backtesting to prove it), not more optimization cleverness.
