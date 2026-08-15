# Captaincy: A Data-Backed Decision Framework

*Compiled 2026-08-15. The deep study on FPL's single biggest points lever (~15-20% of season
score variance; averaging 8 vs 5 pts per captaincy ≈ +114 pts ≈ 200k+ rank places).*

## The core numbers

**2025/26 elite (top-50) captaincy:**
| Player | Share of picks | Avg when captained |
|---|---|---|
| Haaland | 59.3% | ~6.78 |
| Bruno Fernandes | 16.9% | 8.75 |
| Saka | small | 8.86 (best avg) |

The default-volume pick returned ~2 pts/week less than fixture-picked alternatives — yet elite
managers still gave Haaland ~59% of armbands, because no alternative could be *pre-identified*
reliably and Haaland's effective ownership made deviating risky. The champion captained
Haaland 22/38, Bruno 7, nobody else more than twice.

**The strongest deviation datapoint (2024/25):** elite managers captained Bruno on just 0.8%
of picks but averaged **14.73** per captaincy — deviation pays when concentrated on one
pre-identified secondary premium in hand-picked fixtures, never scattered.

**Venue matters ~20-35%** (players average ~3.3-4.5 pts home vs ~2.7-3.2 away; 56% of goals
are scored at home) and it's heterogeneous: Bowen's 4 hauls were ALL at home; Haaland is
unusually venue-insensitive. Per-player home/away splits required, not a global constant.

## Why P(haul) beats mean for captaincy

The armband doubles the whole distribution, so captain choice is dominated by the right tail.
Bruno's season total (235) was below Haaland's (239), but his **12 double-digit hauls vs
Haaland's 9** made him the better per-captaincy asset. Captain EV = P(haul) × upside −
P(blank) × regret, not mean × 2.

**Archetypes by haul rate:** (1) set-piece-taking attacking mids on high-volume teams
(Bruno: ~32% haul rate — pens + FKs + bonus stack); (2) penalty-taking elite forwards
(Haaland); (3) explosive venue-dependent wide players (Bowen — captainable only at home);
(4) consistent accumulators — high floor, poor captains.

## The deviation rule (all conditions required)

Deviate from the default captain when ALL of:
1. Alternative's xPts within **1.5-2.0 pts** of the default (or higher);
2. Default's EO **>70-75%** and alternative's EO **<35-50%**;
3. Fixture trigger: alternative at **home** vs a **bottom-six xGA (last 6, venue-specific)**
   opponent;
4. Not in rank-protection mode.

Stay with the default when its xPts lead ≥2, or its EO is so high a blank-while-deviating
costs you against the whole field. A haul from a 20%-EO captain moves rank 1.5-2× as much as
the same haul from a 60%-EO captain.

## Rank-state framework

| Mode | Rule |
|---|---|
| **Protect** (good rank, late season) | Captain the highest-EO pick; leave only for a ≥2 xPts edge |
| **Neutral** (most weeks) | Full trigger stack above |
| **Chase** (bad rank / trailing mini-league) | Maximize P(15+) among <40% EO options within 2 xPts |

Same pick can be right at 800k and wrong at 15k — rank state is an input, not a tiebreaker.

## Triple Captain playbook

- Success benchmark: **≥14 raw points** (42 TC pts).
- Default to a DGW, but **condition on P(starting both) ≥ 0.8** — the record 1.4M-manager
  DGW36 TC on Haaland returned 11 pts because he sat the second game. Minutes model first.
- Single-GW TC acceptable under chip-expiry pressure: elite premium, home, bottom-six
  opponent (two 48-pt Haaland single-GW TCs in 2025/26 prove it).
- Even perfect spots fail ~1 in 3 (Haaland's blank at home to promoted Leeds).

## Quantified mistakes to hard-block

1. Differential punts without the EO case (double rank hit when the default hauls).
2. Captain roulette — elites concentrate ~76% of picks on 2 players.
3. Form-chasing over fixture-and-venue.
4. Ignoring home/away (the cheapest signal to add).
5. Rank-blind strategy.
6. Abandoning the default after one blank (a ~30% haul-rate process blanks often).
7. TC on hype instead of minutes.

## The algorithm (implementation spec)

Inputs per candidate: simulated score distribution (Poisson on venue/opponent-adjusted
xG/xA + bonus) → xPts, P(blank≤2), P(haul≥10), P(15+); per-player home/away split; opponent
xGA rank (last 6, venue-specific); penalty flag; projected EO; P(start); rank state.

```
pool    = candidates with P(start) ≥ .85 and xMins ≥ 70
default = highest projected-EO premium
best_ev = argmax(0.7·z(P_haul) + 0.3·z(xPts))       # tail-weighted

PROTECT: return best_ev if best_ev.xPts − default.xPts ≥ 2.0 else default
NEUTRAL: return best_ev if (default.EO > .70 and best_ev.EO < .45
                            and default.xPts − best_ev.xPts ≤ 1.5
                            and best_ev.fixture_boost
                            and best_ev.P_haul ≥ default.P_haul) else default
CHASE:   diffs = pool where EO < .40 and xPts gap ≤ 2.0
         return argmax(diffs, P_15plus) if diffs else default

TRIPLE CAPTAIN: fire iff (DGW and P(start both) ≥ .8 and E[GW pts] ≥ 10)
                      or (single GW: home + fixture_boost + E ≥ 8 + chip expiring)
```

Starting calibration constants (revise from our own backtests): stay-gap 2.0 · deviate-gap
1.5 · EO-high 70% · EO-diff 40-45% · haul 10 · TC both-games P ≥ .8 · TC benchmark 14 ·
tail weight 70/30.
