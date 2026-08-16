# FPL-Picker

AI-assisted Fantasy Premier League team picker. It pulls live data from the
official FPL API, scores every player with an expected-points model, and uses
integer-programming optimization to pick the best legal 15-man squad, starting
XI, captain, and vice-captain.

## How it works

1. **Data** (`fpl_picker/api.py`) — fetches `bootstrap-static` (all players,
   teams, gameweeks) and `fixtures` from the official FPL API at
   `https://fantasy.premierleague.com/api/`. No login required.
2. **Scoring** (`fpl_picker/scoring.py`) — projects expected points per player
   over the next few gameweeks by blending:
   - **form** (recent points per game),
   - **season points per game**,
   - **FPL's own `ep_next` estimate**,
   - **underlying numbers** (expected goal involvements per 90),
   adjusted for **availability** (injuries/suspensions, chance of playing) and
   **fixture difficulty** over the chosen horizon, with a decay so nearer
   gameweeks matter more. Double gameweeks count twice, blanks count zero.
3. **Optimization** (`fpl_picker/optimizer.py`) — a single integer linear
   program (via [PuLP](https://coin-or.github.io/pulp/)) that simultaneously
   picks the 15-man squad, the starting XI, and the captain, maximizing
   projected points subject to all FPL rules:
   - £100.0m budget (configurable)
   - 2 GK / 5 DEF / 5 MID / 3 FWD squad shape
   - max 3 players per club
   - legal formation for the XI (1 GK, 3–5 DEF, 2–5 MID, 1–3 FWD)
   - captain doubles their points; bench points are down-weighted

## Quick start

```bash
pip install -r requirements.txt
python -m fpl_picker
```

Useful options:

```bash
python -m fpl_picker --budget 100.0        # budget in £m
python -m fpl_picker --horizon 5           # gameweeks to project over
python -m fpl_picker --lock "Haaland" --lock "Saka"
python -m fpl_picker --exclude "Salah"
python -m fpl_picker --save-data data.json # snapshot API data for offline use
python -m fpl_picker --data data.json      # run offline from a snapshot
```

### The OpenFPL forecaster (recommended from GW2 onward)

FPL-Picker can use the pre-trained, academically validated
[OpenFPL](https://github.com/daniegr/OpenFPL) ensembles (MIT, arXiv:2508.09992)
as its forecaster — accuracy rivaling commercial services. One-time setup:

```bash
pip install -r requirements-openfpl.txt
git clone --depth 1 https://github.com/daniegr/OpenFPL ~/OpenFPL   # ~750MB
```

Then fetch data *with per-player match history* and run:

```bash
python -m fpl_picker --with-history --save-data data.json --openfpl ~/OpenFPL
python -m fpl_picker --data data.json --openfpl ~/OpenFPL --team 1234567
```

Notes: the models need current-season match history, so this mode gives its
best from ~GW2 onward (before that, players fall back to the built-in blend).
`--openfpl-folds 2` trades a little accuracy for much faster loading.

On top of the raw OpenFPL predictions, FPL-Picker applies two correction
layers for the model's known gaps: a **minutes gate** (expected-minutes
multiplier from recent starts — their documented weak spot) and an
**expected defensive-contribution layer** (the 2025/26 rule their training
data pre-dates), computed from per-match defensive stats when the API
provides them. Add `--with-understat` when fetching to fill the
Understat-only features (shots, key passes, xGChain, team xG/xGA/PPDA)
that are otherwise left blank.

### Captaincy

Squad and team reports run the researched captaincy framework
(`docs/research/08-captaincy.md`): a high-ownership premium is rank
insurance, and the armband only deviates when the full trigger stack aligns.
Set your posture with `--rank-mode protect|neutral|chase` — chasing rank
loosens the rules toward differentials, protecting tightens them toward the
field's pick. The reasoning is printed with every selection.

### Rate your team and plan transfers

Once the season's first deadline has passed, point it at your FPL Team ID
(the number in the URL on the Points page at fantasy.premierleague.com):

```bash
python -m fpl_picker --team 1234567
python -m fpl_picker --team 1234567 --free-transfers 2 --max-transfers 3
```

This rates your squad out of 100 against the perfect wildcard squad at your
budget, shows your best XI and captain with no transfers, and evaluates
transfer plans of increasing size with point hits priced in. A hit is only
recommended when it clears the strategy threshold (must gain more than
4 points plus a risk margin over the projection horizon — see
`docs/research/02-winning-strategies.md`). Sell prices are approximated by
current prices, since the public API doesn't expose purchase prices.
Note `--team` fetches live data, so run it from a machine the FPL API
doesn't block (home connections are fine; some cloud hosts are blocked).

## Tests

```bash
python -m pytest tests/ -q
```

Tests run fully offline against synthetic data and verify every FPL squad
constraint (budget, positions, club limit, formation, captaincy).

## Disclaimer

No model wins FPL on its own — this gives you a strong, rules-legal,
data-driven baseline squad and weekly re-picks. Injuries news, rotation, and
your own judgement still matter.
