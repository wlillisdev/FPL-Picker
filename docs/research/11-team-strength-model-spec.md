# Implementation Spec: Team Strength & Clean Sheets (mined from AIrsenal / bpl-next)

*2026-08-16. Extraction from the Alan Turing Institute's AIrsenal and its bpl-next model
package. This is the Phase 2 blueprint for FPL-Picker's clean-sheet / goals-conceded module
— the piece behind every "is this keeper/defender good" question.*

## (a) The team model math

AIrsenal's model is an **extended Dixon-Coles**: independent Poissons per side with the
classic low-score correlation correction, plus Bayesian priors (bpl-next
`extended_dixon_coles.py`). For home team i vs away team j:

```
lambda_home = exp(a_i - d_j + gamma_i)      # a = log attack, d = log defence, gamma = home adv
lambda_away = exp(a_j - d_i)
P(X=x, Y=y) = tau(x,y) · Pois(x; lambda_home) · Pois(y; lambda_away)

tau(0,0) = 1 - c·lh·la;  tau(1,0) = 1 + c·la;  tau(0,1) = 1 + c·lh;  tau(1,1) = 1 - c
tau = 1 otherwise            (c bounded per Dixon-Coles: c ∈ [max(-1/lh,-1/la), min(1/(lh·la),1)])
```

Refinements: per-team home advantage drawn from a hierarchical prior (league mean ~0.1);
attack-defence correlation prior (good attacks tend to be good defences); identifiability
via mean attack = 0; team covariates (they use FIFA game ratings) regress the prior means.
Fit by MCMC (numpyro NUTS) — but the posterior mean ≈ a plain MLE fit for ranking purposes.

## (b) Fitting and recency weighting

- Data: current season + previous 3.
- **Exponential time-decay likelihood weights**: match weight `w = exp(-epsilon · years_ago)`
  with tuned **epsilon = 0.9/year for the team model** (0.2/year for the player model) —
  a 1-year-old match weighs 0.41, 2 years 0.17. This was their fix for the famous
  "stale priors" failure (stacking Chelsea defenders while Chelsea leaked goals).
- Weights rescaled to sum to N (preserves effective sample size vs priors).
- Epsilon was tuned by rolling walk-forward log-probability of real scorelines — the same
  harness style as our Phase 4 plan.

## (c) Clean sheets and goals conceded

Never a single scalar — compute the full goals-conceded pmf from the tau-corrected score
grid (0..10 goals each side):

```
P(clean sheet) = P(opponent scores 0)      # ≈ exp(-lambda_opp)·(1 - c·lh·la) near 0-0
E[defending pts | minutes m, position]:
  if m ≥ 60: + CS_pts[pos] · P(concede 0)          # GK/DEF 4, MID 1
  GK/DEF:    - Σ_n floor(n/2) · (m/90) · P(concede n)
```

Note the DC correction shifts CS probability a couple of percent vs a naive Poisson —
that's the whole point of the correction for FPL purposes.

## (d) The player conditional model (portable, no MCMC)

`ConjugatePlayerModel`: per position, per player, `theta = (p_score, p_assist, p_neither)` —
the probability that a given team goal (while the player is on the pitch) is scored by /
assisted by / unrelated to the player.

- Prior: Dirichlet with position-average involvement split, normalized to 35 pseudo-goals.
- Data: goal involvements scaled by minutes share, time-weighted (0.2/yr).
- Posterior: `Dirichlet(alpha + n)` — a conjugate update, pure numpy, ~30 lines.
- Prediction: for each team-goals count N from the team model pmf, enumerate (goals,
  assists, neither) partitions with the multinomial pmf × FPL point values.

Bonus, saves, cards, defensive contributions: shrunken empirical means
(`(sum + 10·global_mean) / (count + 10)`).

## (e) Promoted teams

No Championship results used. Promoted teams = **prior + external rating covariates with
0.5 extra shrinkage toward (below) the league mean**. Lesson for us: with a plain MLE fit,
promoted teams have zero data — something must be injected (e.g. prior seasons' promoted-
team average strengths, or an external rating).

## (f) Minutes

Their weak point (their own comments say so): recent-minutes scenario averaging (each of
the last N matches' minutes is an equally likely scenario), padded from last season, with
hard zeroing on injury/suspension flags. No starter model. Our `xmins_factor` is already
equivalent-or-better; keep improving ours instead.

## (g) Failure modes they documented

Stale priors (fixed by time decay — port the fix, not the mistake) · wild prior draws
(clip expected goals) · promoted-team overconfidence (shrinkage) · minutes rotation at
season end · goals-conceded timing approximation (subbed-off players) · new-player DB
rebuild pain (own our ID mapping carefully).

## (h) Recommended path for FPL-Picker

**Don't port bpl-next** (jax/numpyro buys uncertainty we don't need for ranking). Options
in order of preference:

1. **`penaltyblog` (pip)**: scipy MLE `DixonColesGoalModel` + `dixon_coles_weights(dates, xi)`
   for the same recency decay. Replaces sections (a)-(b) with a few lines. Caveats: single
   global home advantage, no covariate priors — promoted teams need our own injection.
2. **Roll our own (~150 lines numpy/scipy)**: weighted DC log-likelihood over ~3 seasons
   (`w = exp(-0.9·years)`, rescaled), L-BFGS-B over (a, d, gamma, c) with `Σa = 0`;
   score grid 0..10 → CS probability and goals-conceded pmf → defending points per the
   formula in (c). Promoted teams: prior = mean of last season's promoted teams' fitted
   strengths.
3. **Avoid plain Elo+Poisson**: CS probability needs opponent-attack vs own-defence
   separation, which one Elo scalar conflates; DC-with-decay is barely more code.

The conjugate Dirichlet player model (d) is worth porting too when we want open-play
attacking decomposition — it's the rare Bayesian model that needs no sampler.
