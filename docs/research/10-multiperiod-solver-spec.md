# Implementation Spec: Multi-Period MILP (mined from sertalpbilal/FPL-Optimization-Tools)

*2026-08-16. Line-cited extraction from the de-facto standard open-source FPL solver
(`dev/solver.py`, `solve_multi_period_fpl` at line 261; HiGHS via highspy — every construct
maps 1:1 onto PuLP). This is the Phase 3 blueprint for FPL-Picker.*

## (a) Sets and decision variables

Sets: `P` players (after pruning) · `W` planning gameweeks (capped at 38); `W0` adds the
pre-horizon week holding initial conditions · positions `T`, clubs `C` · bench slots
`O = {0(GK),1,2,3}` · FT states `S = {0..5}` · `P_mod ⊆ P` = current squad members whose
selling price differs from market ("price-modified").

Binary unless noted: `squad[p,w]` (over W0), `squad_fh[p,w]` (parallel Free-Hit squad),
`lineup[p,w]`, `captain[p,w]`, `vicecap[p,w]`, `bench[p,w,o]`, `transfer_in[p,w]`,
`transfer_out_first[p,w]` (sale at stored selling price, P_mod only),
`transfer_out_regular[p,w]` (sale at market); `transfer_out = first + regular`.
Continuous/integer: `in_the_bank[w] ≥ 0`, `fts[w] ∈ 0..5` with one-hot `fts_state[w,s]`,
indicators `ft_above_ub[w]`, `ft_below_lb[w]`, `penalized_transfers[w] ≥ 0`,
`transfer_count[w] ∈ 0..15`. Chips: `use_wc[w]`, `use_bb[w]`, `use_fh[w]`, `use_tc[p,w]`.

Key idea: **squad is a state variable including the pre-horizon week**, so transfers are a
flow-balance constraint; the FH squad is a separate parallel variable family used one week.

## (b) Constraints

Initial conditions: fix `squad[p, next_gw-1]` to the current squad; `in_the_bank[next_gw-1]
= itb`; `fts[next_gw] = initial_ft·(1-use_wc) + base·use_wc`; `fts[w] ≥ 1` for later weeks.

Squad composition (per week): 15-man squad; `Σ lineup = 11 + 4·use_bb`; one bench GK and
three ordered outfield bench slots, all `· (1-use_bb)`; one captain + one vice, both
`≤ lineup`, not the same player; `lineup + Σ_o bench ≤ 1`; positional lineup min/max
(1/3/2/1 to 1/5/5/3, max relaxed by `+use_bb`); squad shape 2/5/5/3; ≤3 per club (and
`squad_fh` mirrors all of it `·use_fh`). FH-week linking: `lineup ≤ squad + use_fh` AND
`lineup ≤ squad_fh + 1 - use_fh` (same for bench) — lineup comes from the FH squad only in
FH weeks.

Transfer flow & budget:
```
squad[p,w] = squad[p,w-1] + transfer_in[p,w] - transfer_out[p,w]
sold[w]   = Σ_{P_mod} sell_price·out_first + Σ buy_price·out_regular
bought[w] = Σ buy_price·transfer_in
itb[w] = itb[w-1] + sold[w] - bought[w]
FH budget: Σ fh_sell_price·squad_fh[w] ≤ itb[w-1] + Σ fh_sell_price·squad[w-1]
transfer_in/out banned in FH weeks; transfer_in + transfer_out ≤ 1 per player-week
```
Sell price computed outside the model: `selling = purchase + (now - purchase)//2` if
profitable else `now` (£0.1m integer units).

**The multiple-sell-event trap fix** (solver.py:569-578) — without it the model sells a
price-modified player cheap, rebuys, and "first-sells" again at profit:
```
out_first[p,w] + out_regular[p,w] ≤ 1          ∀ p∈P_mod, w
Σ_w out_first[p,w] ≤ 1                          ∀ p∈P_mod
horizon · Σ_{w≤ŵ} out_first[p,w] ≥ Σ_{w≥ŵ} out_regular[p,w]   ∀ p∈P_mod, ŵ
```

FT banking (max-5 rolling bank, `clamp(fts - transfers + 1, 1, 5)`) via two indicators and
big-M = 20:
```
raw[w] = fts[w] - transfer_count[w] + 1 - use_wc[w] - use_fh[w]   # chips freeze accrual
ft_above_ub ⟺ raw ≥ 6 → fts[w+1] = 5;  ft_below_lb ⟺ raw ≤ 0 → fts[w+1] = 1
else fts[w+1] = raw[w];   fts[w] = Σ_s s·fts_state[w,s], Σ_s fts_state = 1
```

Hits: `penalized_transfers[w] ≥ num_transfers[w] - fts[w] - 15·use_wc[w]`;
`transfer_count ≤ 15·(1-use_wc)` (wildcard transfers are free and don't consume FTs).

Chips: `use_wc + use_bb + use_fh + Σ_p use_tc ≤ 1` per week; `use_tc[p,w] ≤ captain[p,w]`;
`Σ_w use_X ≤ chip_limits[X]` (default 0 = disabled); `squad_fh[p,w] ≤ use_fh[w]`.
Scheduling controls: force chip in exact GWs, whitelists, forced-window sets, no-chip weeks.

Optional constraints worth porting: locked/banned (locks must bind on `squad + squad_fh`),
`no_transfer_last_gws` (kills phantom end-of-horizon churn — recommended default 1-2),
`num_transfers` forced count (replaces our evaluate_team N-loop), hit limits,
`booked_transfers`, `transfer_itb_buffer` (price-change insurance), `max_defenders_per_team`
(covariance hedge), `no_opposing_play` (don't start players facing each other).

## (c) Objective

```
gw_xp[w] = Σ_p pts[p,w]·(lineup + captain + 0.1·vicecap + use_tc + Σ_o bench_weight[o]·bench)
gw_total[w] = gw_xp[w] - 4·penalized_transfers[w] + gw_ft_gain[w]
              - ft_use_penalty·transfer_count[w] + 0.08·in_the_bank[w]
maximize Σ_w gw_total[w] · decay^(w - next_gw)        # decay default 0.84 (preset 0.9)
```
Defaults: bench weights {GK .03, 1st .21, 2nd .06, 3rd .002}; vice weight 0.1 (needed or the
solver assigns it arbitrarily). **FT value is state-dependent and piecewise**: marginal
values {2nd FT: 2.0, 3rd: 1.6, 4th: 1.3, 5th: 1.1} accumulated into `ft_state_value[s]`,
and the objective takes the per-week *delta* `gw_ft_value[w] - gw_ft_value[w-1]` — credit
when banking, paid back when spending, so the model doesn't burn FTs at horizon end.

## (d) Chip mechanics summary

WC: transfers free, FT accrual frozen. FH: parallel one-week squad, persistent chain
untouched, transfers banned, budget at sell-valuation. BB: lineup = 15, bench empty.
TC: third multiple of one player's points. Chip *scheduling* in practice is enumeration —
a grid of chip-week combinations solved in parallel and ranked (run/run_parallel.py) —
not one giant free solve.

## (e) Tractability

- **Pruning is the big lever** (solver.py:161-196): keep a "safe" set (current squad, locks,
  top-EV%), drop players with horizon xMins < 100-300 and bottom EV-per-price percentile.
  ~700 → ~150-250 players.
- HiGHS parallel, time limit 600-1200s, mip gap 0 (loosen to 0.01-0.1% for long horizons).
  No warm starts. Horizons 5-8 GWs are the norm.
- Alternative solutions: no-good cuts on next-GW transfers (`Σ_{fixed=1}(1-x) +
  Σ_{fixed=0}x ≥ 1`) re-solved N times → "top-k transfer plans".
- Randomization for robustness: `pts += pts·(92 - xMins)/134·N(0,1)·strength` — noise
  scales inversely with minutes certainty; many solves aggregated into "% of plans making
  this move" (run/simulations.py, run/sensitivity.py).

## (f) Input schema

Projection CSV, one row per player: `ID, Name, Pos, Value, Team, {gw}_Pts, {gw}_xMins ...`
(ID = official element id; per-GW expected points with blanks 0 / doubles pre-summed, plus
expected minutes). Team state = the FPL my-team JSON (picks with purchase/selling prices,
bank, FT limit); reconstructable from public endpoints by replaying all transfers.

## (g) Incremental path for fpl_picker

1. New `multiperiod.py`: extend `scoring.score_players` to expose per-GW point vectors
   (fixture multipliers already exist per-GW).
2. Core skeleton without chips: squad-state flow, budget with dual sell variables +
   multiple-sell fix, fixed FT count.
3. FT banking block (port verbatim — the fiddly part).
4. Chips: WC + BB + TC first (cheap), FH last (parallel squad family). Gate behind
   chip_limits=0 defaults. Thin `plan_chips()` enumeration wrapper.
5. Pruning + CBC hygiene (`PULP_CBC_CMD(timeLimit=600, gapRel=0.001)`), or HiGHS if
   available. Horizon 5 first.
6. Options passthrough: booked transfers, no_transfer_last_gws, hit limits, forced counts.
7. Robustness layer: no-good iteration + minutes-scaled randomization aggregation, feeding
   strategy.py's advice output.

Pitfalls to carry deliberately: integer sell-price formula; never two first-sales; WC
transfers must not consume/accrue FTs; FH must leave the persistent chain untouched;
vice-captain needs its small positive weight.
