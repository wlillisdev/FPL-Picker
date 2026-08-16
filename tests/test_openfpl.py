import math
import os

import pytest

from fpl_picker import openfpl

OPENFPL_DIR = os.environ.get("OPENFPL_DIR", "/workspace/daniegr/openfpl")


def test_window_means_basic():
    rows = [{"total_points": p} for p in [2, 6, 4]]
    means = openfpl._window_means(rows, "total_points")
    assert means[1] == 4.0  # last match
    assert means[3] == 4.0  # mean of all three
    assert means[5] == 4.0  # window bigger than history -> mean of available
    assert means[38] == 4.0


def test_window_means_empty_is_nan():
    means = openfpl._window_means([], "total_points")
    assert all(math.isnan(v) for v in means.values())


def test_team_match_logs_ranks_and_goals():
    bootstrap = {"teams": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]}
    fixtures = [
        {"event": 1, "finished": True, "team_h": 1, "team_a": 2,
         "team_h_score": 3, "team_a_score": 0, "kickoff_time": "a"},
        {"event": 1, "finished": True, "team_h": 3, "team_a": 4,
         "team_h_score": 1, "team_a_score": 1, "kickoff_time": "b"},
        {"event": 2, "finished": True, "team_h": 2, "team_a": 3,
         "team_h_score": 2, "team_a_score": 1, "kickoff_time": "c"},
        {"event": 3, "finished": False, "team_h": 1, "team_a": 3,
         "team_h_score": None, "team_a_score": None},
    ]
    logs = openfpl.team_match_logs(bootstrap, fixtures)
    assert [m["goals_scored"] for m in logs[1]] == [3]
    assert [m["goals_scored"] for m in logs[2]] == [0, 2]
    # Before GW2, team 1 leads (win, +3 GD); team 2 is bottom (loss, -3).
    assert logs[2][1]["rank"] == 4
    assert len(logs[3]) == 2  # unfinished fixture excluded


@pytest.fixture
def mini_data():
    bootstrap = {
        "events": [
            {"id": 1, "is_next": False, "is_current": True, "finished": True},
            {"id": 2, "is_next": True, "is_current": False},
        ],
        "teams": [{"id": 1, "short_name": "AAA"}, {"id": 2, "short_name": "BBB"}],
        "elements": [
            {"id": 10, "element_type": 3, "team": 1, "web_name": "Alpha",
             "now_cost": 60, "status": "a"},
            {"id": 11, "element_type": 4, "team": 2, "web_name": "Beta",
             "now_cost": 80, "status": "a"},
        ],
    }
    fixtures = [
        {"event": 1, "finished": True, "team_h": 1, "team_a": 2,
         "team_h_score": 2, "team_a_score": 1, "kickoff_time": "a"},
        {"event": 2, "finished": False, "team_h": 2, "team_a": 1,
         "team_h_score": None, "team_a_score": None},
    ]
    history = {
        "10": [{"total_points": 8, "minutes": 90, "goals_scored": 1,
                "expected_goals": "0.6", "bps": 30}],
    }
    return {"bootstrap": bootstrap, "fixtures": fixtures, "history": history}


def test_build_samples(mini_data):
    feature_names = [
        "home", "player fpl points 5", "player minutes played 1",
        "player xg 5", "player shots 5", "team goals scored 5",
    ]
    samples = openfpl.build_samples(mini_data, feature_names, horizon=3)
    by_id = {s["player_id"]: s for s in samples}
    assert set(by_id) == {10, 11}

    alpha = by_id[10]
    assert alpha["position"] == "MID"
    assert alpha["home"] == 0.0  # GW2 fixture is away for team 1
    assert alpha["player fpl points 5"] == 8.0
    assert alpha["player minutes played 1"] == 90.0
    assert alpha["player xg 5"] == 0.6
    assert math.isnan(alpha["player shots 5"])  # Understat-only -> NaN
    assert alpha["team goals scored 5"] == 2.0
    assert alpha["_has_history"] is True

    beta = by_id[11]
    assert beta["_has_history"] is False
    assert math.isnan(beta["player fpl points 5"])


needs_models = pytest.mark.skipif(
    not os.path.isdir(os.path.join(OPENFPL_DIR, "models")),
    reason="OpenFPL clone with models not available",
)


@needs_models
def test_engine_reproduces_published_predictions():
    """Our engine must reproduce OpenFPL's own predictions.csv exactly."""
    import csv

    engine = openfpl.OpenFPLEngine(OPENFPL_DIR)
    with open(os.path.join(OPENFPL_DIR, "data", "samples.csv")) as f:
        raw = list(csv.DictReader(f))
    with open(os.path.join(OPENFPL_DIR, "data", "predictions.csv")) as f:
        expected = {r["player"]: float(r["prediction"]) for r in csv.DictReader(f)}

    samples = []
    for r in raw:
        if r["position"] not in engine.models:  # skip AM (assistant managers)
            continue
        row = {"position": r["position"], "player": r["player"]}
        for name in engine.feature_names:
            if name == "home":
                row[name] = 1.0 if r["home"] == "True" else 0.0
            else:
                row[name] = float(r[name]) if r[name] != "" else float("nan")
        samples.append(row)

    engine.predict(samples)
    for row in samples:
        assert abs(row["prediction"] - expected[row["player"]]) < 1e-3, row["player"]
