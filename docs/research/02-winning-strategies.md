# Research: How Winning FPL Managers Actually Win

*Compiled 2026-08-15 from web research (agent report). Informs the FPL-Picker strategy engine.*

## (a) Quantified behaviors of winners

### Skill is real and identifiable
The University of Limerick study of ~1M managers
([PLOS ONE 2021](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0246698),
[arXiv](https://arxiv.org/abs/2009.01206)) found:
- **Manager ranks are correlated across seasons** — skill persists; FPL is not a lottery over 38 GWs.
- Prime success factors are **long-term planning and consistently good decisions under noise**,
  not one-off hero calls.
- **Each year of experience ≈ +22.1 points** on average
  ([Full90 summary](https://full90fpl.com/fpls-great-skill-vs-luck-debate-who-is-right-and-why-is-it-everyone/)).
- Skilled managers' squads **converge to "template" teams** at multiple points in the season —
  elite herding is rational.

### Transfers and hits
- Top managers make **fewer moves and avoid hits**; under the 5-rolled-transfer rules some GWs see
  all tiers averaging **0.0 hits**.
- Average top-10k manager: roughly **10.7 hits (-4s) per season** (~43 points spent) —
  used but rationed ([FPL Oracle](https://fploracle.team/blog/fpl-rank-percentile)).
- Break-even rule: a -4 must be expected to return **>4 points more than the player sold, over
  the holding horizon** — not just one week.

### Team value
- Top-100k/10k managers run squads worth **£102.5m+** on average — flexibility and better benches.
- Value **correlates with rank but causation is unproven** — partly a byproduct of picking good
  players early ([Full90](https://full90fpl.com/does-team-value-matter-in-fpl/)).

### Season benchmarks
- Top 10k ≈ **2,300–2,450 points (~60–65/GW)**. Recent champions: Låbakk 2023/24 won with
  **2,799** (by 51); Budisin 2024/25 by 23; Ibsen 2025/26 by 38.

### Early vs late season
- Elite managers **start steady and low-risk**, avoid heavy-turnover teams, gather 4–6 GWs of
  minutes/form data before structural moves.
- Late season flips to **DGW/BGW navigation, chip choreography**, and rank-protection (shadow
  high-EO picks when ahead).

## (b) Chip playbook (verified current rules)

- **2025/26 onward: two full chip sets** — Wildcard, Free Hit, Bench Boost, Triple Captain in
  *each half* (8 chips total). First-half set **expires at the GW19 deadline**; second set from
  GW20 ([Premier League](https://www.premierleague.com/en/news/4362027/whats-new-in-202526-fantasy-two-sets-of-chips)).
- The Assistant Manager chip (2024/25 only) was removed. **2026/27 keeps the 8-chip format**;
  also live rank updates, BPS tweaks to reduce overlap with defensive-contribution points, up to
  5 rolled free transfers
  ([2026/27 changes](https://www.premierleague.com/en/news/4679873/all-you-need-to-know-about-changes-to-fpl-for-202627)).

### What winners actually did
- **First Wildcard: GW4 modal among the 2025/26 Top 50**, right after the first international
  break; experts converge on **GW4–8**.
- **Second Wildcard: big Top-50 spike at GW32**, used to **build the chip plan** — load DGW33
  teams, pre-solve the following blank.
- **Canonical end-game: WC (GW32) → Bench Boost (DGW33) → Free Hit (BGW34)**, saving transfers
  toward a possible DGW36.
- **Bench Boost**: pair with a Wildcard the week before, target a DGW. Single-GW BB ≈ 8–12 pts;
  **DGW BB ≈ 15–25 pts** ([FPL Copilot](https://fplcopilot.com/blog/chip-strategy-guide)).
- **Triple Captain**: on your premium's **best double gameweek**.
- **Free Hit**: hold for the biggest blank (or an unfieldable monster DGW).
- Chip value overall: **~+49 points from optimal timing vs none** (best +73, worst +2); optimal
  vs *random* timing ≈ 20–30 pts, best vs second-best plan ≈ 3 — **avoiding bad timing matters
  more than perfecting it** ([FPL Copilot](https://fplcopilot.com/blog/fpl-chip-strategy-2026-27)).
- With GW19 expiry, first-half chips can't be hoarded: use on soft targets (first-half
  mini-doubles, fixture runs, injury crises) rather than losing them.

## (c) Captaincy strategy

**Captaincy is the single biggest controllable points lever.**
- **~25% of season points come from the captain's doubled score** (up to ~30%). Budisin 29.1%,
  Låbakk 21.4%.
- Elite captaincy is **overwhelmingly template**: Haaland captaincy >96% in top 10k in peak
  weeks. 2025/26 champion Ibsen captained Haaland 22/38 GWs — philosophy: *keep the armband
  safe, take risks in the other 10 starters*
  ([interview](https://www.premierleague.com/en/news/4672128/fpl-champion-how-to-pick-your-captain-and-maximise-your-chips)).
- **Effective Ownership (EO) math**: EO = starters% + captain% (+TC%). Rules of thumb: if the
  highest-EO captain is also **≥2 xPts clear → captain him regardless**; if within 1–1.5 xPts,
  lower-EO captains are correct *only when chasing rank*; when **protecting** rank take the
  high-EO captain ([FPL Oracle framework](https://fploracle.team/blog/fpl-captaincy-strategy)).

## (d) Squad structure principles

- Every elite squad carries **at least one premium captaincy anchor** (Haaland-class).
- 2025/26 Top-50 defense spending was **balanced**: best defender ~£6.4–6.5m, second ~£5.5m,
  rest £4.0–5.0m — not "big at the back".
- **Premium anchor + rotating value**: mid-price slots chosen by fixture runs, swapped cheaply.
- **Set-piece/penalty duty is a mispriced edge**: a penalty ≈ 0.76–0.79 xG; a regular taker adds
  **~25–40 pts/season** ([Opta Analyst](https://theanalyst.com/articles/fpl-set-piece-stats-projections-tips-premier-league-2026-27)).
- **Fixture-run targeting**: look 3–4 GWs ahead, buy before ownership surges. Fixture quality
  drives **~60%+ of defender points but only ~30–40% of premium attacker points** — rotate
  defense on fixtures, hold premium attackers through bad fixtures; home FDR 3 often beats away
  FDR 2.
- **Defensive-contribution points (2025/26+)** made high-tackle/CBI outfielders (Tarkowski,
  Caicedo) season-keeper value — champion Ibsen picked them from GW1 on that basis.
- **Template core + few well-timed differentials**: e.g. Ibsen holding João Pedro when 388k
  sold (19-pt hat-trick took him 8th → 1st); Låbakk buying Palmer in GW11 before the crowd.

## (e) Rank 1 vs top 10k — and behaviors to avoid

- Skill sets the floor; variance swings most managers 50k–200k ranks/season. Winning outright =
  top-10k-grade process **plus** upside variance captured through a few correct contrarian calls.
- Shared champion traits: **EV/analytics-driven decisions**, safe template captaincy +
  differential outfield, disciplined chip choreography, going early on emerging players.
  2019/20 winner Joshua Bull (Oxford mathematician): **"maths and patience"**.

### Losing behaviors (documented)
1. **Knee-jerk transfers chasing last week's points** (405k bought Alderete after a 17-pt GW;
   he returned 0 next week).
2. **Habitual hits** without a multi-week EV case.
3. **Early chip panic** (GW1–3, before minutes data exists).
4. **Price-change obsession** — value only matters as future flexibility.
5. **Captaincy heroism** — low-EO armband punts while not behind.
6. **Abandoning the plan after one bad week.**

## (f) Concrete rules a software system can encode

**Transfers**
1. Optimize xPts over a **4–6 GW horizon**, never 1 GW.
2. Hit only if `ΔxPts(horizon) > 4 + risk_margin` (margin ≈ 2); soft cap ~10 hits/season.
3. Roll transfers toward known DGWs/restructures (max bank = 5).
4. Never transfer purely off one GW's actual points; require underlying xGI/minutes signal ≥ N weeks.

**Captaincy**
5. Default captain = highest-xPts premium. If `xPts(top) − xPts(alt) ≥ 2` → captain top regardless of EO.
6. Within 1–1.5 xPts: chasing → lower-EO candidate; protecting → highest-EO candidate.
7. Weight captain-suitability (nailed premium, pens, home fixture) heavily in squad construction.

**Chips (8-chip era, GW19 expiry)**
8. WC1 window **GW4–8**, ideally at an international break; earlier only on ≥3 forced transfers.
9. Sequence each half: **WC → BB on best DGW → FH on worst blank → TC on the anchor's best double**.
10. **Never let a chip expire unused**; from ~3 GWs before expiry, play the best remaining opportunity.
11. TC condition: premium DGW, both fixtures FDR ≤ 3. BB condition: ≥13/15 players with
    acceptable xMins, ideally post-wildcard DGW.

**Squad structure**
12. One premium anchor always; balanced defense; rotate mid-price slots on fixtures.
13. Bonus for penalty/set-piece duty and defensive-contribution profiles.
14. Weight fixtures ~2× more for defenders/keepers than premium attackers; home/away-adjusted;
    plan 3–4 GWs ahead.
15. Track top-10k EO; template core by default; cap deliberate differentials at ~2–3 slots,
    deployed only when chasing rank.

**Meta/guardrails**
16. Benchmark: ~2,350+ pts pace ⇒ top-10k; monitor weekly.
17. Rank-state machine: `chasing` → accept variance; `protecting` → shadow field EO.
18. Anti-tilt: forbid same-week reactive sales of players whose underlying stats remain strong;
    price changes are a tiebreaker only.
