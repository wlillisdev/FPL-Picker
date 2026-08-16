# FPL-Picker — System Blueprint

*Synthesized 2026-08-15 from four research studies (full reports in [`docs/research/`](docs/research/)):
open-source systems, winning-manager strategy, prediction science, and the competitive landscape.*

## Vision

**The reference open-source, end-to-end FPL engine**: transparent projections + full-rules
optimization + season strategy in one free, installable, scriptable package. The market research
is unambiguous — xPts tables and freemium web solvers are saturated, but *nobody* ships the whole
pipeline open source. OpenFPL has a model but no product; sertalpbilal's solver has no bundled
projections. That seam is ours.

An honest goal-setting note up front: even a **perfect** prediction model achieves only R² ≈ 0.15
on single-gameweek points — FPL is dominated by irreducible variance. What is achievable and
proven (PLOS ONE, 1M-manager study) is that **process skill persists across seasons**. The
system's job is to play top-10k-grade process every single week; winning outright then requires
variance breaking our way, which the system maximizes exposure to but cannot guarantee.

## The three gaps that define "serious"

Everything in the roadmap serves closing these, identified independently by multiple studies:

1. **Team-ID import + multi-period transfer/chip solving** — from-scratch squad picking (what we
   have) is a wildcard tool, useful ~2 weeks a season. The weekly question is "which 1–2
   transfers, is a −4 worth it, when do I chip?"
2. **A minutes model** — P(start)/P(60+ min) errors dwarf every other error source. This is the
   single biggest accuracy differentiator between reference models and naive ones.
3. **Uncertainty quantification** — report "this transfer was optimal in 78% of perturbed
   solves", not one fragile point-estimate plan.

## Target architecture

```
┌────────────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                         │
│  • FPL API collector (bootstrap, fixtures, element-summary,        │
│    entry/{id} picks) with snapshot cache (--save-data/--data)      │
│  • Historical store: vaastav dataset (2016-25) + our own per-GW    │
│    snapshots going forward, keyed on official FPL element IDs      │
│  • Understat xG/xA ingest; optional odds ingest                    │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ PROJECTION ENGINE  (per player, per future GW)                     │
│  minutes module  → P(start), P(sub), P(≥60)   ← manual overrides   │
│  team module     → implied xG for/against, P(clean sheet)          │
│  attack module   → opponent-adjusted npxG/xA per 90 + penalty share│
│  sundries        → bonus, saves, cards, defensive contributions    │
│  assembly        → Monte-Carlo sim → mean xPts + P(haul > 4)       │
│  horizon: 8 GWs, decay 0.84/GW (configurable)                      │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ STRATEGY ENGINE (rules from winning-manager research)              │
│  hit threshold (>4 + margin) · FT banking value · EO/captaincy     │
│  policy · chip windows & sequencing · anti-tilt guardrails         │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ OPTIMIZER — multi-period MILP (PuLP now, HiGHS later)              │
│  squad/XI/captain/bench-order/transfers per GW over horizon        │
│  chips as binary activation vars · hits priced in objective        │
│  sensitivity wrapper: re-solve under perturbed inputs              │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ INTERFACES                                                         │
│  CLI (now) → JSON output → thin web UI ("rate my team") → agent/   │
│  library API                                                       │
└────────────────────────────────────────────────────────────────────┘
```

Design principles locked in by the research:

- **Projections and solver stay decoupled** behind a clean interface (why sertalpbilal's solver
  outlived its projection source).
- **Decomposition model first, ML later** — simple models with good features match complex ones
  in this domain; a LightGBM layer is an optional single-digit-% upgrade at the end.
- **Own the data collection** (vaastav stopped updating; vendors go dark) and keep scoring rules
  config-driven (FPL changes rules yearly — defensive-contribution points 2025/26, 8-chip
  format with GW19 expiry, 2026/27 live scoring).
- **API-independent test fixtures** and per-GW data validation (AIrsenal's pipeline-rot lesson).
- **Regress finishing skill (G−xG) to zero**; use npxG + penalty share, never raw goals.
- **Bookmaker odds or Elo/Dixon-Coles for team strength — never the official FDR** (except as
  UI garnish).

## Roadmap

### Phase 0 — Foundation ✅ (shipped)
CLI picker: FPL API fetch + snapshot mode, blended scoring with fixture-difficulty decay,
single MILP for squad/XI/captain under all FPL rules, offline test suite.

### Phase 1 — Weekly usefulness (next)
The features that make this a tool you run every gameweek:
- **Team-ID import**: fetch your real squad, bank, and free transfers from
  `/api/entry/{id}/event/{gw}/picks/`.
- **Transfer suggester**: best 0/1/2 transfers over the horizon; hits allowed only when
  `ΔxPts > 4 + risk margin`; respects sell-price rules.
- **Rate-my-team**: score your squad vs the optimal one.
- **Data resilience**: snapshot workflow hardening + a mirror fallback for hosts where the FPL
  API is IP-blocked (e.g. PythonAnywhere).

### Phase 2 — Projection engine v1
Two-track (see [`docs/research/09-code-review-openfpl-solpaul.md`](docs/research/09-code-review-openfpl-solpaul.md)):
**Track A — OpenFPL integration**: build the 235-feature samples builder (FPL API +
Understat, rolling windows {1,3,5,10,38}) and run OpenFPL's MIT-licensed pre-trained
ensembles as the base forecaster — near-commercial accuracy without training anything.
**Track B — our correction layers on top** (where OpenFPL is provably weak): minutes
gate, DefCon points (post-2024 rule it has never seen), 2026/27 bonus adjustments.
Plus the original decomposition components as fallback/complement:
- Minutes module (starts share, status flags, congestion + manual override file).
- Team module (Elo/Dixon-Coles from results; odds when available) → P(clean sheet).
- Attack module (opponent-adjusted npxG/xA per 90, penalty takers).
- Defensive-contribution, bonus, saves sub-models. Assembly by simulation.
- Historical ingest (vaastav + Understat) for calibration.

### Phase 3 — Multi-period planner + chips
- Transfers as decision variables over an 8-GW horizon; FT banking (max 5) with terminal value;
  hits priced.
- Chips as activation variables with the strategy engine's windows: WC1 in GW4–8 at an
  international break; each half sequenced WC → BB on best DGW → FH on worst blank → TC on the
  anchor's best double; never let a chip expire at GW19/38.
- Captaincy/EO policy: safe template armband by default; differential rules only when chasing.

### Phase 4 — Trust: backtesting + uncertainty
- Walk-forward backtest harness on historical seasons, scored per position and per
  return-category vs naive baseline and FPL's official xP. Published in the repo.
- Sensitivity wrapper: N re-solves under perturbed projections → robustness % per decision.

### Phase 5 — Reach
- Thin web UI (rate-my-team + optimal squad + suggested transfer), JSON/library API for agents,
  scheduled weekly runs.

## Strategy rules the system encodes

From the winning-manager research (full list in
[`docs/research/02-winning-strategies.md`](docs/research/02-winning-strategies.md)):

| # | Rule |
|---|------|
| 1 | Optimize over 4–6+ GWs, never 1 |
| 2 | Hit only if ΔxPts(horizon) > 4 + ~2 margin; soft cap ~10 hits/season |
| 3 | Roll transfers toward DGWs (bank max 5) |
| 4 | No transfers off one week's actual points without underlying xGI/minutes signal |
| 5 | Captain = highest-xPts premium; ≥2 xPts clear → always; within 1.5 → EO policy by rank state |
| 6 | Always carry one premium captaincy anchor; ~25% of season points come from the armband |
| 7 | Balanced defense (~£6.5m + £5.5m + budget); rotate mid-price slots on fixtures |
| 8 | Bonus weight for penalty/set-piece duty (+25–40 pts/season) and defensive-contribution profiles |
| 9 | Fixtures matter ~2× more for defenders than premium attackers; hold premiums through bad runs |
| 10 | Chip windows per half; never forfeit a chip; DGW BB ≈ 15–25 pts, optimal chip timing ≈ +49 pts |
| 11 | Anti-tilt: no reactive sales of players whose underlying numbers are strong; prices are tiebreakers |
| 12 | Pace benchmark: ~2,350+ points = top-10k pace; rank-state machine (chasing → variance, protecting → shadow EO) |

## Known risks

- **FPL API blocks cloud-host IPs** (already hit on PythonAnywhere) → snapshot workflow +
  mirror fallback are first-class features, not afterthoughts.
- **Yearly rule changes** → scoring constants and chip rules live in config, revisited each July.
- **Accuracy reputation** → we publish backtests before making claims.
- **Variance** → communicate P(haul), robustness %, and honest ceilings everywhere; never
  promise ranks.
