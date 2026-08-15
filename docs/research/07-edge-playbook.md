# The Edge Playbook: When to Deviate from the Template

*Compiled 2026-08-15 from contrarian-strategy research. The rules here are designed to be
implemented in the strategy engine. Core finding: blanket contrarianism loses; targeted
deviation on uncorrelated information wins.*

## Proven contrarian patterns

1. **Buy on underlying volume before returns arrive.** xG *volume* (not conversion, not
   being-"due") predicts future goals. The crowd's ownership follows returns with a 1–3 GW
   lag — the buy window is the week the underlying stats turn, not the week the hauls print
   ([FFS xG-delta study](https://www.fantasyfootballscout.co.uk/2024/05/08/can-we-predict-goals-using-a-negative-xg-delta)).
2. **Hold through slumps when underlying stats hold.** Knee-jerk data is stark: 841k managers
   bought Woltemade after a haul → 2 pts next week; 235k sold Van de Ven after a blank → 23
   pts next week. Reacting to last week's points is negative-EV
   ([FPL Optimizer knee-jerk series](https://www.fpl-optimizer.com/blog/2025-10-27-gw9-kneejerk-check)).
3. **Rule-change exploitation (annual, highest ROI).** Re-simulate last season under new rules
   every July; flag players whose recalculated totals diverge >10% from market perception.
   DefCon-2025/26 proved this wins titles.
4. **Early adoption of role changes and promoted-team assets** — the information is public
   before the ownership arrives.
5. **The market frame**: the field exhibits sunk-cost bias, herding, and recency bias
   ([Forbes hedge-fund analysis](https://www.forbes.com/sites/stevendesmyter/2025/05/20/fantasy-premier-leaguelessons-from-the-hedge-fund-trading-floor/)).
   The whole edge is systematically taking the other side.

## Fixture targeting (odds, never official FDR)

Methodology: de-margin bookmaker 1X2 + O/U 2.5 → implied team xG for/against → clean-sheet
probability. Buy target-team assets **one GW before** a run where 6-GW average difficulty
≤ 2.5; sell one GW before a red cliff.

**2026/27 opening six (consensus):**
- **Target:** Everton, Liverpool, Man Utd, Newcastle (joint-best 2.83 avg FDR), Arsenal,
  Man City, Leeds (ticker-topping but source disagreement — verify with odds).
- **Avoid:** Bournemouth and Coventry (joint-worst 3.6), Fulham, Hull (3.4).
- **Sell-before-the-cliff:** Sunderland — soft GW1-2, then Arsenal and City from GW3.

## Structural positions verdict

- **No-premium/spread**: only correct when no player projects >~1.3× the next tier. It's a
  bet on a flat top end — catastrophic when a premium goes nuclear.
- **Zero-forward (5-4-1 style)**: grounded in a real inefficiency (forwards have worst PPM),
  partially repaired by 2026/27 reclassifications.
- **Big-at-the-back**: legitimized by DefCon; trimmed (not killed) by the CBI-bonus nerf.
- **Keeper rotation pairs: trap.** One trusted keeper + £4.0m fodder beats active rotation.
- **Meta-rule:** structure is never the edge; the edge is spotting when pricing/rules make a
  structure *temporarily* correct.

## Price/timing

- Team value correlates with rank (~0.51) but causation runs through good picks. Best
  managers accrue ~£2-3m as a byproduct.
- Legit edge = sequencing only: execute already-decided transfers before the rise/fall.
  Hard-block any transfer whose sole justification is value.

## The good-differential checklist

Ownership <10% (standard), <5% deep. ALL required:
1. Strong underlying stats (xGI/90, shot volume — not recent output)
2. Secure minutes (the #1 killer of bad differentials)
3. An upcoming fixture swing the crowd hasn't priced
4. A points-path story (pens, set pieces, role change, DefCon eligibility)

Sizing: 1–2 differential slots on a template core. Differential captain only when template
captain EO > 75%, alternative within 1.5 xPts, and posture = climb.

## Mini-league mode

- **Leading**: shadow/block — converge on the chaser's team, especially their captain.
- **Chasing**: compute EO against the mini-league, not global; take variance.
- ≤8 GWs left in a race: optimize P(win) via simulation, not E[points].

## Expert consensus: how to use it

No quantified evidence experts beat the template on picks; their value is **early adoption**
(they move on fixture swings and role news 1–2 GWs before ownership). Use expert consensus as
a candidate generator and news feed, never as a decision layer above the EV model. Highest-
confidence deviation = our model and experts agree *against* the template.

## Implementable trigger rules (for the strategy engine)

Deviate from template ONLY on one of six triggers:
1. **Leading-indicator buy**: xGI/90 (last 4-6 GWs) ≥ elite threshold AND ownership < 15%
   AND xMins ≥ 85 AND next-6 odds-implied fixtures ≤ median.
2. **Anti-knee-jerk**: never sell on blanks if rolling xGI within 20% of baseline; never buy
   on hauls unless underlying moved; sell premiums when underlying decays ≥30% over 4+ GWs.
3. **Rule-delta scan** every July (see 2026/27 deltas in 06-2026-27-scouting.md).
4. **Fixture-swing front-running** (odds-implied, 1 GW ahead of the crowd).
5. **Differential sizing** per the checklist above.
6. **Price timing** as sequencing only.

Posture state machine: `risk_mode ∈ {protect, neutral, climb}` scales differential count,
captain EO tolerance, and chip aggression.

**Hard-coded anti-patterns:** blanket contrarianism · keeper rotation pairs · ideological
structures · buying for price rises · selling on blanks with intact underlying stats ·
official FDR as ground truth.
