"""OpenFPL integration: run daniegr/OpenFPL's pre-trained ensembles as our forecaster.

OpenFPL (MIT, https://github.com/daniegr/OpenFPL, arXiv:2508.09992) ships
per-position XGBoost ensembles trained on FPL + Understat data whose accuracy
rivals commercial services. This module builds prediction samples in its
235-feature format from our API snapshot (best effort: FPL-only features are
filled; Understat-only features are left NaN, which the pipeline tolerates)
and aggregates per-fixture predictions into horizon scores for the optimizer.

Feature semantics (verified against the shipped samples.csv): each stat is a
per-match MEAN over rolling windows of the last {1, 3, 5, 10, 38} matches.
Early in a season, windows shrink to however many matches exist; with no
history at all a player's features are NaN and predictions are unreliable —
this engine is designed for use from ~GW2 onward.

Requires: pandas, numpy, joblib, scikit-learn, xgboost (see
requirements-openfpl.txt) and a local clone of the OpenFPL repository.
"""

import os
import warnings

WINDOWS = (1, 3, 5, 10, 38)

# scaler feature name prefix -> key in the per-match history rows we build.
# None means the stat is Understat-only and left NaN (the model's scaler
# pipeline nan_to_num's it; accuracy degrades gracefully).
PLAYER_STATS = {
    "player fpl points": "total_points",
    # "relevant" points is OpenFPL's position-filtered points; total points is
    # the closest available approximation from the FPL API.
    "player relevant fpl points": "total_points",
    "player minutes played": "minutes",
    "player influence": "influence",
    "player creativity": "creativity",
    "player threat": "threat",
    "player goals scored": "goals_scored",
    "player penalties missed": "penalties_missed",
    "player assists": "assists",
    "player goals conceded": "goals_conceded",
    "player own goals": "own_goals",
    "player saves": "saves",
    "player penalties saved": "penalties_saved",
    "player yellow cards": "yellow_cards",
    "player red cards": "red_cards",
    "player bps": "bps",
    "player fpl bonus points": "bonus",
    "player xg": "expected_goals",
    "player xa": "expected_assists",
    # Understat-only stats: filled when --with-understat merged them into the
    # history rows, NaN otherwise.
    "player shots": "us_shots",
    "player xgchain": "us_xgchain",
    "player xgbuildup": "us_xgbuildup",
    "player key passes": "us_key_passes",
}
TEAM_STATS = {
    "team goals scored": "goals_scored",
    "team goals conceded": "goals_conceded",
    "team league rank": "rank",
    "team opponent league rank": "opponent_rank",
    "team xg": "us_xg",
    "team xga": "us_xga",
    "team deep": "us_deep",
    "team deep allowed": "us_deep_allowed",
    "team ppda att": "us_ppda_att",
    "team ppda def": "us_ppda_def",
    "team ppda allowed att": "us_ppda_allowed_att",
    "team ppda allowed def": "us_ppda_allowed_def",
}
POSITIONS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def _window_means(rows, key, upto=None):
    """Per-match means of ``key`` over each window, newest matches last.

    Returns {window: mean or NaN}. ``upto`` limits history to the first N rows
    (used in tests / retrospective sample building).
    """
    values = []
    for row in rows[:upto]:
        v = row.get(key)
        if v is not None:
            try:
                values.append(float(v))
            except (TypeError, ValueError):
                pass
    out = {}
    for w in WINDOWS:
        tail = values[-w:]
        out[w] = sum(tail) / len(tail) if tail else float("nan")
    return out


def team_match_logs(bootstrap, fixtures):
    """Per-team chronological logs of finished fixtures with goals and rank."""
    finished = [
        f
        for f in fixtures
        if f.get("finished")
        and f.get("team_h_score") is not None
        and f.get("event") is not None
    ]
    finished.sort(key=lambda f: (f["event"], f.get("kickoff_time") or ""))

    points = {t["id"]: 0 for t in bootstrap["teams"]}
    goal_diff = {t["id"]: 0 for t in bootstrap["teams"]}
    logs = {t["id"]: [] for t in bootstrap["teams"]}

    def current_ranks():
        order = sorted(
            points, key=lambda t: (-points[t], -goal_diff[t])
        )
        return {team: i + 1 for i, team in enumerate(order)}

    for f in finished:
        ranks = current_ranks()
        h, a = f["team_h"], f["team_a"]
        hs, as_ = f["team_h_score"], f["team_a_score"]
        logs[h].append(
            {"goals_scored": hs, "goals_conceded": as_, "rank": ranks[h], "opponent_rank": ranks[a]}
        )
        logs[a].append(
            {"goals_scored": as_, "goals_conceded": hs, "rank": ranks[a], "opponent_rank": ranks[h]}
        )
        points[h] += 3 if hs > as_ else (1 if hs == as_ else 0)
        points[a] += 3 if as_ > hs else (1 if hs == as_ else 0)
        goal_diff[h] += hs - as_
        goal_diff[a] += as_ - hs
    return logs


def build_samples(data, feature_names, horizon=5):
    """Build OpenFPL-format sample rows for every player's upcoming fixtures.

    ``data`` is our API snapshot and must contain ``history`` (per-player
    per-match logs from the element-summary endpoint, added by
    ``api.fetch_data(with_history=True)``). Returns a list of dicts:
    metadata (player_id, position, event, gw_offset) plus one entry per
    feature name.
    """
    import math

    bootstrap = data["bootstrap"]
    fixtures = data["fixtures"]
    history = data.get("history") or {}
    from .api import next_event_id

    start_event = next_event_id(bootstrap)
    team_logs = team_match_logs(bootstrap, fixtures)

    # Merge Understat team rows (chronological, same finished matches) into
    # the team logs by order so team us_* windows can be computed.
    for team_id_str, us_rows in (data.get("understat_teams") or {}).items():
        log = team_logs.get(int(team_id_str))
        if log:
            for row, us in zip(log, us_rows):
                row.update({k: v for k, v in us.items() if k != "date"})

    upcoming = {}
    for f in fixtures:
        event = f.get("event")
        if event is None or not (start_event <= event < start_event + horizon):
            continue
        upcoming.setdefault(f["team_h"], []).append((event, f["team_a"], True))
        upcoming.setdefault(f["team_a"], []).append((event, f["team_h"], False))

    samples = []
    for element in bootstrap["elements"]:
        position = POSITIONS.get(element["element_type"])
        if position is None:
            continue
        rows = history.get(str(element["id"])) or history.get(element["id"]) or []
        player_means = {
            prefix: _window_means(rows, key) if key else {w: float("nan") for w in WINDOWS}
            for prefix, key in PLAYER_STATS.items()
        }
        team_id = element["team"]
        tlog = team_logs.get(team_id, [])
        team_means = {
            prefix: _window_means(tlog, key) if key else {w: float("nan") for w in WINDOWS}
            for prefix, key in TEAM_STATS.items()
        }

        for event, opponent_id, home in sorted(upcoming.get(team_id, [])):
            row = {
                "player_id": element["id"],
                "position": position,
                "event": event,
                "gw_offset": event - start_event,
                "home": home,
            }
            has_data = bool(rows)
            for name in feature_names:
                if name == "home":
                    row[name] = float(home)
                    continue
                filled = False
                for prefix, means in list(player_means.items()) + list(team_means.items()):
                    for w in WINDOWS:
                        if name == f"{prefix} {w}":
                            row[name] = means[w]
                            filled = True
                            break
                    if filled:
                        break
                if not filled:
                    row[name] = float("nan")
            row["_has_history"] = has_data
            samples.append(row)
    return samples


class OpenFPLEngine:
    """Loads the OpenFPL scalers/models and predicts points per fixture."""

    def __init__(self, openfpl_dir, folds=5):
        import joblib

        models_dir = os.path.join(openfpl_dir, "models")
        if not os.path.isdir(models_dir):
            raise ValueError(
                f"{openfpl_dir} doesn't look like an OpenFPL clone (no models/ "
                "directory). Clone https://github.com/daniegr/OpenFPL first."
            )
        self.xscaler = joblib.load(os.path.join(models_dir, "xscaler.save"))
        self.yscaler = joblib.load(os.path.join(models_dir, "yscaler.save"))
        self.position_features = joblib.load(os.path.join(models_dir, "features.save"))
        self.feature_names = list(self.xscaler.feature_names_in_)

        self.models = {}
        for position in ("GK", "DEF", "MID", "FWD"):
            members = []
            for cv in range(1, folds + 1):
                search_dir = os.path.join(models_dir, f"cv{cv}_{position}")
                if not os.path.isdir(search_dir):
                    continue
                with open(os.path.join(search_dir, "search.txt")) as f:
                    log = f.read()
                top = [
                    x.split(" ")[0]
                    for x in log.split("The population is:")[-1].split("Candidate ")[1:]
                ]
                for candidate in top:
                    cdir = os.path.join(search_dir, candidate)
                    fname = os.listdir(cdir)[0]
                    members.append(joblib.load(os.path.join(cdir, fname)))
            if not members:
                raise ValueError(f"No models found for position {position}")
            self.models[position] = members

    def predict(self, samples):
        """Median-ensemble prediction for each sample row (adds 'prediction')."""
        import numpy as np

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for position, members in self.models.items():
                rows = [s for s in samples if s["position"] == position]
                if not rows:
                    continue
                X = np.array(
                    [[r[name] for name in self.feature_names] for r in rows],
                    dtype="float32",
                )
                X = np.nan_to_num(
                    self.xscaler.transform(np.nan_to_num(X).astype("float32"))
                ).astype("float32")
                idx = [
                    self.feature_names.index(f) for f in self.position_features[position]
                ]
                X = X[:, idx]
                preds = [
                    self.yscaler.inverse_transform(m.predict(X).reshape(-1, 1)).ravel()
                    for m in members
                ]
                for row, value in zip(rows, np.median(preds, axis=0)):
                    row["prediction"] = float(value)
        return samples


def xmins_factor(rows, recent=5):
    """Expected-minutes multiplier from recent starts, addressing OpenFPL's
    documented weak spot (predicting who won't play).

    Uses the last ``recent`` matches: full starts (60'+) count 1.0, sub
    appearances count by minutes share, absences count 0. Floor of 0.05 so a
    fringe player is heavily discounted rather than erased.
    """
    tail = rows[-recent:]
    if not tail:
        return 1.0  # no evidence -> leave the prediction alone
    total = 0.0
    for row in tail:
        minutes = row.get("minutes") or 0
        total += 1.0 if minutes >= 60 else minutes / 90.0
    return max(total / len(tail), 0.05)


# 2025/26+ defensive-contribution rule: +2 pts for hitting the per-match
# threshold. DEF: 10 CBIT; MID/FWD: 12 CBIT + tackles + recoveries.
DEFCON_POINTS = 2.0
DEFCON_THRESHOLDS = {"DEF": 10, "MID": 12, "FWD": 12}
DEFCON_KEYS = (
    "clearances_blocks_interceptions",
    "tackles",
    "recoveries",
    "defensive_contribution",
)


def expected_defcon(rows, position, recent=10):
    """Expected DefCon points per match — the rule OpenFPL's models pre-date.

    Prefers the API's per-match ``defensive_contribution`` points field when
    present; otherwise reconstructs the threshold hit-rate from raw defensive
    stats. Returns 0.0 when the data carries neither (e.g. goalkeepers or
    pre-2025 datasets). Hit rates are computed over started matches only and
    are highly persistent (see docs/research/05-case-study-2025-26.md).
    """
    threshold = DEFCON_THRESHOLDS.get(position)
    if threshold is None:
        return 0.0
    started = [r for r in rows[-recent:] if (r.get("minutes") or 0) >= 60]
    if not started:
        return 0.0
    # Shrink small samples toward zero: a 100% hit rate over one match is
    # weak evidence; full credibility from 3 started matches.
    credibility = min(len(started) / 3.0, 1.0)

    if any(r.get("defensive_contribution") is not None for r in started):
        values = [float(r.get("defensive_contribution") or 0) for r in started]
        return credibility * sum(values) / len(values)

    hits = 0
    counted = 0
    for r in started:
        cbit = r.get("clearances_blocks_interceptions")
        tackles = r.get("tackles")
        recoveries = r.get("recoveries")
        if cbit is None and tackles is None and recoveries is None:
            continue
        counted += 1
        volume = float(cbit or 0)
        if position in ("MID", "FWD"):
            volume += float(tackles or 0) + float(recoveries or 0)
        if volume >= threshold:
            hits += 1
    return credibility * DEFCON_POINTS * hits / counted if counted else 0.0


def score_with_openfpl(
    data,
    openfpl_dir,
    horizon=5,
    decay=0.85,
    folds=5,
    minutes_gate=True,
    defcon=True,
    min_history=4,
):
    """Full pipeline: build samples, predict, correct, aggregate.

    Corrections applied on top of the raw OpenFPL predictions:
    - minutes gate (their documented weak spot: zeros/blanks)
    - expected DefCon points (a rule their training data pre-dates)
    - reliability gate: players with fewer than ``min_history`` played
      matches keep no OpenFPL score (caller falls back to the blend).
      With tiny samples every rolling window collapses to the same one-match
      mean and the models extrapolate single-game flukes into season-long
      form — one big DefCon opener must not make a £4.0m defender the
      "best player in the game".
    Returns ({player_id: horizon score}, {player_id: next-GW score},
    n_predicted, n_without_history).
    """
    from .scoring import availability

    engine = OpenFPLEngine(openfpl_dir, folds=folds)
    samples = build_samples(data, engine.feature_names, horizon=horizon)
    engine.predict(samples)

    elements = {e["id"]: e for e in data["bootstrap"]["elements"]}
    history = data.get("history") or {}
    scores = {}
    next_scores = {}
    no_history = set()
    for row in samples:
        if "prediction" not in row:
            continue
        if not row["_has_history"]:
            no_history.add(row["player_id"])
            continue
        pid = row["player_id"]
        rows = history.get(str(pid)) or history.get(pid) or []
        played = [r for r in rows if (r.get("minutes") or 0) > 0]
        if len(played) < min_history:
            no_history.add(pid)
            continue
        per_fixture = max(row["prediction"], 0.0)
        if defcon:
            per_fixture += expected_defcon(rows, row["position"])
        if minutes_gate:
            per_fixture *= xmins_factor(rows)
        per_fixture *= availability(elements[pid])
        scores[pid] = scores.get(pid, 0.0) + per_fixture * (decay ** row["gw_offset"])
        if row["gw_offset"] == 0:
            next_scores[pid] = next_scores.get(pid, 0.0) + per_fixture
    return scores, next_scores, len(scores), len(no_history)
